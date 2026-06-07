import argparse
import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path


SORT_COLUMNS = {
    "like": "ytLike",
    "view": "ytView",
}


@dataclass(frozen=True)
class Config:
    input_path: str
    output_dir: str
    sort_keys: list[str]
    descending: bool


def main(argv: list[str] | None = None) -> int:
    try:
        cfg = parse_config(sys.argv[1:] if argv is None else argv)
        output_paths = run(cfg)
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1

    for output_path in output_paths:
        print(output_path)
    return 0


def parse_config(args: list[str]) -> Config:
    parser = argparse.ArgumentParser(
        prog="sort_youtube_metrics",
        usage="%(prog)s [--by view|like|both] [--ascending] [--output-dir DIR] <input-csv>",
        add_help=True,
    )
    parser.add_argument(
        "--by",
        choices=["view", "like", "both"],
        default="both",
        help="metric to sort by; defaults to both",
    )
    parser.add_argument(
        "--ascending",
        action="store_true",
        help="sort from lowest to highest instead of highest to lowest",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="directory for sorted CSV files; defaults to the input file directory",
    )
    parser.add_argument("input_csv")
    namespace = parser.parse_args(args)

    input_path = Path(namespace.input_csv)
    output_dir = namespace.output_dir or str(input_path.parent or Path("."))
    sort_keys = list(SORT_COLUMNS) if namespace.by == "both" else [namespace.by]

    return Config(
        input_path=namespace.input_csv,
        output_dir=output_dir,
        sort_keys=sort_keys,
        descending=not namespace.ascending,
    )


def run(cfg: Config) -> list[str]:
    with open(cfg.input_path, newline="", encoding="utf-8-sig") as input_file:
        rows = list(csv.DictReader(input_file))
        if input_file.seekable():
            input_file.seek(0)
        fieldnames = read_fieldnames(cfg.input_path)

    if not fieldnames:
        raise ValueError("input csv is empty")

    output_dir = Path(cfg.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths: list[str] = []
    for sort_key in cfg.sort_keys:
        column = SORT_COLUMNS[sort_key]
        sorted_rows = sort_rows(rows, column, descending=cfg.descending)
        output_path = output_dir / output_filename(cfg.input_path, sort_key)
        if same_file_path(cfg.input_path, str(output_path)):
            raise ValueError("input and output CSV paths must be different")
        write_csv(output_path, fieldnames, sorted_rows)
        output_paths.append(str(output_path))

    return output_paths


def read_fieldnames(input_path: str) -> list[str]:
    with open(input_path, newline="", encoding="utf-8-sig") as input_file:
        reader = csv.reader(input_file)
        return next(reader, [])


def sort_rows(
    rows: list[dict[str, str]], column: str, descending: bool = True
) -> list[dict[str, str]]:
    if rows and column not in rows[0]:
        raise ValueError(f"input csv is missing {column} column")

    return sorted(
        rows,
        key=lambda row: metric_sort_value(row.get(column, "")),
        reverse=descending,
    )


def metric_sort_value(value: str) -> int:
    normalized = value.strip().replace(",", "")
    if not normalized:
        return 0
    try:
        return int(normalized)
    except ValueError as exc:
        raise ValueError(f"metric value is not an integer: {value}") from exc


def output_filename(input_path: str, sort_key: str) -> str:
    path = Path(input_path)
    return f"{path.stem}-sorted-by-{sort_key}{path.suffix}"


def write_csv(
    output_path: Path, fieldnames: list[str], rows: list[dict[str, str]]
) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def same_file_path(left: str, right: str) -> bool:
    return os.path.abspath(left) == os.path.abspath(right)


if __name__ == "__main__":
    raise SystemExit(main())
