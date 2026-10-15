import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "scanner", ROOT / "skills/migrate-sonar-to-agent-api/scripts/scan_sonar_usage.py"
)
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


class SearchBudgetTests(unittest.TestCase):
    def test_only_nested_tool_budgets_are_exempt(self):
        cases = [
            ('tools=[{"type": "web_search", "max_tokens": 2000}]', False),
            ('tools=[{\n"max_tokens": 2000,\n"type": "web_search"\n}]', False),
            ('responses.create(\n tools=[{"type": "web_search"}],\n max_tokens=100,\n)', True),
            ('payload={"tools": [{"type": "web_search"}], "max_tokens": 100}', True),
            ('payload={"max_tokens_per_page": 2000, "max_tokens": 100}', True),
            ('tools=[{"type": "web_search", "max_tokens": 2000}]; max_tokens=100', True),
            ('tools=[{"type": "web_search"}, {"type": "other", "max_tokens": 100}]', True),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                findings, _ = scanner.scan_lines(source.splitlines())
                self.assertEqual(any(row[3] == "Sonar request param" for row in findings), expected)

    def test_grader_rejects_request_budget_next_to_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.py"
            source = '''response = client.responses.create(
    tools=[{"type": "web_search", "max_tokens": 2000}],
    max_output_tokens=100,
)
search_results = response.status
'''
            path.write_text(source)
            grader = Path(__file__).with_name("check.sh")
            accepted = subprocess.run([str(grader), directory, "--style", "sdk"], capture_output=True, text=True)
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            path.write_text(source.replace("max_output_tokens=100,", "max_output_tokens=100, max_tokens=100,"))
            rejected = subprocess.run([str(grader), directory, "--style", "sdk"], capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)
            self.assertIn("FAIL leftover:", rejected.stdout)


if __name__ == "__main__":
    unittest.main()
