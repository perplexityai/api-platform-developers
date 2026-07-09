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
    completion = client.chat.completions.create(
        model="sonar",
        messages=[
            {"role": "user", "content": f"Give a factual snapshot of the company {company}."}
        ],
        max_tokens=200,
        response_format={
            "type": "json_schema",
            "json_schema": {"schema": SNAPSHOT_SCHEMA},
        },
    )
    return json.loads(completion.choices[0].message.content)


def main():
    company = sys.argv[1] if len(sys.argv) > 1 else "Nvidia"
    print(json.dumps(fetch_snapshot(company), indent=2))


if __name__ == "__main__":
    main()
