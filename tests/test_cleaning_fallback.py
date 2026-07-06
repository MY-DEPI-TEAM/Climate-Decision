import unittest
from unittest.mock import patch

from lakehouse.silver import cleaning


class CleaningFallbackTests(unittest.TestCase):
    def setUp(self):
        cleaning._cached_df = None

    @patch("warehouse.silver.cleaning._load_local_fallback_df")
    @patch("warehouse.silver.cleaning._clean_df")
    def test_get_cleaned_df_falls_back_when_source_pipeline_fails(self, mock_clean_df, mock_load_local_fallback_df):
        fallback_df = object()
        mock_clean_df.side_effect = [RuntimeError("simulated JDBC failure"), fallback_df]
        mock_load_local_fallback_df.return_value = fallback_df

        result = cleaning.get_cleaned_df()

        self.assertIs(result, fallback_df)


if __name__ == "__main__":
    unittest.main()
