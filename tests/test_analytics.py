import base64
import json
import unittest
from unittest.mock import MagicMock, patch

from gateway.analytics import AnalyticsAgentClient, AnalyticsResult


class AnalyticsAgentClientTest(unittest.TestCase):
    def test_build_pdf_report_decodes_backend_pdf(self) -> None:
        client = AnalyticsAgentClient("http://agent.local")
        payload = {
            "filename": "report.pdf",
            "pdf_b64": base64.b64encode(b"%PDF-test").decode("utf-8"),
        }
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")

        with patch("urllib.request.urlopen", return_value=response):
            filename, pdf_bytes = client.build_pdf_report(
                "Which country leads revenue?",
                AnalyticsResult(insight="Germany leads."),
            )

        self.assertEqual(filename, "report.pdf")
        self.assertEqual(pdf_bytes, b"%PDF-test")


if __name__ == "__main__":
    unittest.main()

