import importlib.util
import pathlib
import unittest


MODULE_PATH = pathlib.Path(__file__).parents[1] / "src" / "sort_youtube_metrics.py"
SPEC = importlib.util.spec_from_file_location("sort_youtube_metrics", MODULE_PATH)
assert SPEC is not None
sortmetrics = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(sortmetrics)


class SortYoutubeMetricsTests(unittest.TestCase):
    def test_sort_rows_by_metric_descending(self):
        rows = [
            {"title": "low", "ytView": "100"},
            {"title": "high", "ytView": "1,200"},
            {"title": "empty", "ytView": ""},
        ]

        sorted_rows = sortmetrics.sort_rows(rows, "ytView")

        self.assertEqual([row["title"] for row in sorted_rows], ["high", "low", "empty"])

    def test_sort_rows_by_metric_ascending(self):
        rows = [
            {"title": "low", "ytLike": "100"},
            {"title": "high", "ytLike": "1200"},
            {"title": "empty", "ytLike": ""},
        ]

        sorted_rows = sortmetrics.sort_rows(rows, "ytLike", descending=False)

        self.assertEqual([row["title"] for row in sorted_rows], ["empty", "low", "high"])

    def test_sort_rows_requires_metric_column(self):
        with self.assertRaisesRegex(ValueError, "missing ytView column"):
            sortmetrics.sort_rows([{"title": "Episode"}], "ytView")

    def test_metric_sort_value_rejects_non_integer(self):
        with self.assertRaisesRegex(ValueError, "not an integer"):
            sortmetrics.metric_sort_value("unknown")


if __name__ == "__main__":
    unittest.main()
