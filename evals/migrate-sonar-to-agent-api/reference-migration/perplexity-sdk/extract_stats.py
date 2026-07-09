import json
import sys

from perplexity import Perplexity

SNAPSHOT_SCHEMA = {
    "type": "object",
    "properties": {
        "company": {"type": "string"},
        "headquarters": {"type": "string"},
        "founded_year": {"type": "integer"},
        "one_line_summary": {"type": "string"},
    },
    "required": ["company", "headquarters", "founded_year", "one_line_summary"],
}


def fetch_snapshot(company):
    client = Perplexity()
    response = client.responses.create(
        model="perplexity/sonar",
        input=f"Give a factual snapshot of the company {company}.",
        tools=[{"type": "web_search"}],
        max_output_tokens=200,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "company_snapshot", "schema": SNAPSHOT_SCHEMA},
        },
    )
    if response.status != "completed":
        raise RuntimeError(response.error or response.incomplete_details)
    return json.loads(response.output_text)


def main():
    company = sys.argv[1] if len(sys.argv) > 1 else "Nvidia"
    print(json.dumps(fetch_snapshot(company), indent=2))


if __name__ == "__main__":
    main()
