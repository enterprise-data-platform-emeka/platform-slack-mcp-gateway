import unittest

from gateway.analytics import AnalyticsResult
from gateway.formatting import allowed_channel, extract_question, format_answer


class FormattingTest(unittest.TestCase):
    def test_extract_question_removes_slack_mentions(self) -> None:
        text = "<@U123ABC> Which country has the highest revenue?"
        self.assertEqual(extract_question(text), "Which country has the highest revenue?")

    def test_allowed_channel_allows_all_when_empty(self) -> None:
        self.assertTrue(allowed_channel("random", set()))

    def test_allowed_channel_requires_match_when_configured(self) -> None:
        self.assertTrue(allowed_channel("analytics-agent-demo", {"analytics-agent-demo"}))
        self.assertFalse(allowed_channel("general", {"analytics-agent-demo"}))

    def test_format_answer_includes_enterprise_metadata(self) -> None:
        result = AnalyticsResult(
            insight="Germany had the highest revenue.",
            assumptions=["Revenue means completed payments."],
            bytes_scanned=2048,
            cost_usd=0.001234,
            chart_type="bar",
            sql="SELECT * FROM edp_dev_gold.revenue_by_country LIMIT 10",
            request_id="req-123",
        )

        message = format_answer(result, streamlit_url="http://my-alb:8501")

        self.assertIn("Germany had the highest revenue.", message)
        self.assertIn("Revenue means completed payments.", message)
        self.assertIn("cost: `$0.001234`", message)
        self.assertIn("chart: `bar`", message)
        self.assertIn("http://my-alb:8501", message)
        # noise removed from Slack message
        self.assertNotIn("SELECT", message)
        self.assertNotIn("req-123", message)
        self.assertNotIn("scanned:", message)


if __name__ == "__main__":
    unittest.main()

