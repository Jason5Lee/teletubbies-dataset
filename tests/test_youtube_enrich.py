import importlib.util
import io
import pathlib
import unittest


MODULE_PATH = pathlib.Path(__file__).parents[1] / "src" / "youtube_enrich.py"
SPEC = importlib.util.spec_from_file_location("youtube_enrich", MODULE_PATH)
assert SPEC is not None
ytenrich = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ytenrich)


class StubFetcher:
    def __init__(self, infos):
        self.infos = infos
        self.seen_ids = []

    def fetch_video_infos(self, yt_ids):
        self.seen_ids = yt_ids
        return {yt_id: self.infos[yt_id] for yt_id in yt_ids if yt_id in self.infos}


class YtEnrichTests(unittest.TestCase):
    def test_enrich_csv_adds_youtube_columns_without_title(self):
        input_csv = (
            "overall,season,wikiUrl,title,airdates,ytId\n"
            "1,S01E01,/wiki/Ned%27s_Bicycle,Ned's Bicycle,31 March 1997,Tnw4Ze2tBIo\n"
            "2,S01E02,/wiki/Our_Pig_Winnie,Our Pig Winnie,1 April 1997,_6zLAGb9pVM\n"
        )
        output = io.StringIO()

        missing_ids = ytenrich.enrich_csv(
            io.StringIO(input_csv),
            output,
            StubFetcher(
                {
                    "Tnw4Ze2tBIo": ytenrich.VideoInfo(
                        like_count="123", view_count="4567"
                    )
                }
            ),
        )

        expected = (
            "overall,season,wikiUrl,title,airdates,ytId,ytLike,ytView\n"
            "1,S01E01,/wiki/Ned%27s_Bicycle,Ned's Bicycle,31 March 1997,Tnw4Ze2tBIo,123,4567\n"
            "2,S01E02,/wiki/Our_Pig_Winnie,Our Pig Winnie,1 April 1997,_6zLAGb9pVM,,\n"
        )
        self.assertEqual(output.getvalue(), expected)
        self.assertEqual(missing_ids, ["_6zLAGb9pVM"])

    def test_enrich_csv_drops_existing_title_and_refreshes_counts(self):
        input_csv = (
            "overall,season,wikiUrl,title,airdates,ytId,ytTitle,ytLike,ytView\n"
            "1,S01E01,/wiki/Ned%27s_Bicycle,Ned's Bicycle,31 March 1997,Tnw4Ze2tBIo,old title,1,2\n"
        )
        output = io.StringIO()

        missing_ids = ytenrich.enrich_csv(
            io.StringIO(input_csv),
            output,
            StubFetcher(
                {
                    "Tnw4Ze2tBIo": ytenrich.VideoInfo(
                        like_count="123", view_count="4567"
                    )
                }
            ),
        )

        expected = (
            "overall,season,wikiUrl,title,airdates,ytId,ytLike,ytView\n"
            "1,S01E01,/wiki/Ned%27s_Bicycle,Ned's Bicycle,31 March 1997,Tnw4Ze2tBIo,123,4567\n"
        )
        self.assertEqual(output.getvalue(), expected)
        self.assertEqual(missing_ids, [])

    def test_build_youtube_api_url_preserves_credentials(self):
        request_url = ytenrich.build_youtube_api_url(
            "https://example.test/videos?alt=json", ["abc123", "missing"], "key-123"
        )

        self.assertIn("alt=json", request_url)
        self.assertIn("part=snippet%2Cstatistics", request_url)
        self.assertIn("id=abc123%2Cmissing", request_url)
        self.assertIn("key=key-123", request_url)


if __name__ == "__main__":
    unittest.main()
