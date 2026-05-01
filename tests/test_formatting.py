import unittest

from gateway.analytics import AnalyticsResult
from gateway.formatting import allowed_channel, extract_question, format_answer, format_footer


class FormattingTest(unittest.TestCase):
    def test_extract_question_removes_slack_mentions(self) -> None:
        text = "<@U123ABC> Which country has the highest revenue?"
        self.assertEqual(extract_question(text), "Which country has the highest revenue?")

    def test_allowed_channel_allows_all_when_empty(self) -> None:
        self.assertTrue(allowed_channel("random", set()))

    def test_allowed_channel_requires_match_when_configured(self) -> None:
        self.assertTrue(allowed_channel("analytics-agent-demo", {"analytics-agent-demo"}))
        self.assertFalse(allowed_channel("general", {"analytics-agent-demo"}))

    def test_format_answer_summary_only(self) -> None:
        result = AnalyticsResult(
            insight="Germany had the highest revenue.",
            assumptions=["Revenue means completed payments."],
            cost_usd=0.001234,
            chart_type="bar",
        )

        message = format_answer(result, streamlit_url="http://my-alb:8501")

        self.assertIn("> Germany had the highest revenue.", message)
        self.assertIn("<http://my-alb:8501|View full report in Streamlit>", message)
        # cost and assumptions not in primary message — in footer reply after PDF
        self.assertNotIn("cost:", message)
        self.assertNotIn("Revenue means completed payments.", message)

    def test_format_footer_contains_cost_and_assumptions(self) -> None:
        result = AnalyticsResult(
            insight="Germany leads.",
            assumptions=["Revenue means completed payments.", "No date filter applied."],
            cost_usd=0.001234,
            chart_type="bar",
        )
        text = format_footer(result)
        self.assertIn("cost: `$0.001234`", text)
        self.assertIn("chart: `bar`", text)
        self.assertIn("*Assumptions*", text)
        self.assertIn("> Revenue means completed payments.", text)
        self.assertIn("> No date filter applied.", text)

    def test_format_footer_no_assumptions_still_shows_cost(self) -> None:
        result = AnalyticsResult(insight="Germany leads.", cost_usd=0.000048, assumptions=[])
        text = format_footer(result)
        self.assertIn("cost: `$0.000048`", text)
        self.assertNotIn("Assumptions", text)


if __name__ == "__main__":
    unittest.main()

