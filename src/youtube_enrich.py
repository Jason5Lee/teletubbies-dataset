import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol


DEFAULT_YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_BATCH_SIZE = 50
ENRICHMENT_COLUMNS = ["ytLike", "ytView"]
DROPPED_COLUMNS = {"ytTitle"}


@dataclass(frozen=True)
class Config:
    input_path: str
    output_path: str
    api_key: str
    access_token: str


@dataclass(frozen=True)
class VideoInfo:
    like_count: str
    view_count: str


class VideoInfoFetcher(Protocol):
    def fetch_video_infos(self, yt_ids: list[str]) -> dict[str, VideoInfo]:
        ...


class YouTubeClient:
    def __init__(
        self,
        api_url: str = DEFAULT_YOUTUBE_API_URL,
        api_key: str = "",
        access_token: str = "",
        timeout: float = 30.0,
    ) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.access_token = access_token
        self.timeout = timeout

    def fetch_video_infos(self, yt_ids: list[str]) -> dict[str, VideoInfo]:
        results: dict[str, VideoInfo] = {}
        for start in range(0, len(yt_ids), YOUTUBE_BATCH_SIZE):
            batch_results = self._fetch_video_info_batch(
                yt_ids[start : start + YOUTUBE_BATCH_SIZE]
            )
            results.update(batch_results)
        return results

    def _fetch_video_info_batch(self, yt_ids: list[str]) -> dict[str, VideoInfo]:
        request_url = build_youtube_api_url(self.api_url, yt_ids, self.api_key)
        request = urllib.request.Request(request_url)
        if self.access_token:
            request.add_header("Authorization", f"Bearer {self.access_token}")

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            body = exc.read(4096).decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"youtube api returned {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"call youtube api: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"decode youtube api response: {exc}") from exc

        results: dict[str, VideoInfo] = {}
        for item in payload.get("items", []):
            statistics = item.get("statistics", {})
            results[item.get("id", "")] = VideoInfo(
                like_count=str(statistics.get("likeCount", "")),
                view_count=str(statistics.get("viewCount", "")),
            )
        return results


def main(argv: list[str] | None = None) -> int:
    try:
        cfg = parse_config(sys.argv[1:] if argv is None else argv)
        run(cfg)
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def parse_config(args: list[str]) -> Config:
    parser = argparse.ArgumentParser(
        prog="youtube_enrich",
        usage="%(prog)s [-api-key key | -access-token token] <input-csv> <output-csv>",
        add_help=True,
    )
    parser.add_argument("-api-key", default="", help="YouTube Data API key")
    parser.add_argument(
        "-access-token",
        "-token",
        dest="access_token",
        default="",
        help="OAuth bearer access token for the YouTube Data API",
    )
    parser.add_argument("input_csv")
    parser.add_argument("output_csv")
    namespace = parser.parse_args(args)

    if bool(namespace.api_key) == bool(namespace.access_token):
        parser.error("provide exactly one of -api-key or -access-token")

    return Config(
        input_path=namespace.input_csv,
        output_path=namespace.output_csv,
        api_key=namespace.api_key,
        access_token=namespace.access_token,
    )


def run(cfg: Config) -> None:
    if same_file_path(cfg.input_path, cfg.output_path):
        raise ValueError("input and output CSV paths must be different")

    client = YouTubeClient(api_key=cfg.api_key, access_token=cfg.access_token)
    with open(cfg.input_path, newline="", encoding="utf-8") as input_file:
        with open(cfg.output_path, "w", newline="", encoding="utf-8") as output_file:
            missing_ids = enrich_csv(input_file, output_file, client)

    if missing_ids:
        print(
            "warning: no YouTube metadata returned for "
            f"{len(missing_ids)} video IDs: {', '.join(missing_ids)}",
            file=sys.stderr,
        )


def same_file_path(left: str, right: str) -> bool:
    return os.path.abspath(left) == os.path.abspath(right)


def enrich_csv(input_file, output_file, fetcher: VideoInfoFetcher) -> list[str]:
    records = list(csv.reader(input_file))
    if not records:
        raise ValueError("input csv is empty")

    header = records[0]
    indexes = column_indexes(header)
    if "ytId" not in indexes:
        raise ValueError("input csv is missing ytId column")

    output_header, output_indexes, source_indexes = build_output_header(header)
    yt_id_index = indexes["ytId"]
    yt_ids = collect_unique_values(records[1:], yt_id_index)
    video_infos = fetcher.fetch_video_infos(yt_ids) if yt_ids else {}

    writer = csv.writer(output_file, lineterminator="\n")
    writer.writerow(output_header)

    seen_missing: set[str] = set()
    missing_ids: list[str] = []
    for record in records[1:]:
        row = build_output_row(record, output_header, source_indexes)
        yt_id = field_at(record, yt_id_index)
        if yt_id:
            if yt_id in video_infos:
                info = video_infos[yt_id]
                row[output_indexes["ytLike"]] = info.like_count
                row[output_indexes["ytView"]] = info.view_count
            elif yt_id not in seen_missing:
                seen_missing.add(yt_id)
                missing_ids.append(yt_id)
        writer.writerow(row)

    return missing_ids


def column_indexes(header: list[str]) -> dict[str, int]:
    return {column: index for index, column in enumerate(header)}


def build_output_header(
    header: list[str],
) -> tuple[list[str], dict[str, int], list[int | None]]:
    output_header: list[str] = []
    source_indexes: list[int | None] = []
    for index, column in enumerate(header):
        if column in DROPPED_COLUMNS:
            continue
        output_header.append(column)
        source_indexes.append(index)

    indexes = column_indexes(output_header)
    for column in ENRICHMENT_COLUMNS:
        if column in indexes:
            continue
        indexes[column] = len(output_header)
        output_header.append(column)
        source_indexes.append(None)

    return output_header, indexes, source_indexes


def build_output_row(
    record: list[str], output_header: list[str], source_indexes: list[int | None]
) -> list[str]:
    row: list[str] = []
    for source_index in source_indexes:
        if source_index is None:
            row.append("")
        else:
            row.append(record[source_index] if source_index < len(record) else "")

    while len(row) < len(output_header):
        row.append("")
    return row


def collect_unique_values(records: list[list[str]], column_index: int) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for record in records:
        value = field_at(record, column_index)
        if not value or value in seen:
            continue
        seen.add(value)
        values.append(value)
    return values


def field_at(record: list[str], index: int) -> str:
    if index < 0 or index >= len(record):
        return ""
    return record[index].strip()


def build_youtube_api_url(api_url: str, yt_ids: list[str], api_key: str) -> str:
    parsed_url = urllib.parse.urlparse(api_url)
    query = dict(urllib.parse.parse_qsl(parsed_url.query))
    query["part"] = "snippet,statistics"
    query["id"] = ",".join(yt_ids)
    if api_key:
        query["key"] = api_key
    return urllib.parse.urlunparse(
        parsed_url._replace(query=urllib.parse.urlencode(query))
    )


if __name__ == "__main__":
    raise SystemExit(main())
