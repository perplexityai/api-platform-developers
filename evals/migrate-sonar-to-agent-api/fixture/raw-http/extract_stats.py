import json
import os
import sys

import requests

API_URL = "https://api.perplexity.ai/chat/completions"

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

def fetch_snapshot(company: str) -> dict:
    api_key = os.environ["PERPLEXITY_API_KEY"]
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "user", "content": f"Give a factual snapshot of the company {company}."}
        ],
        "max_tokens": 200,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"schema": SNAPSHOT_SCHEMA},
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)

def main() -> None:
    company = sys.argv[1] if len(sys.argv) > 1 else "Nvidia"
    snapshot = fetch_snapshot(company)
    print(json.dumps(snapshot, indent=2))

if __name__ == "__main__":
    main()
