import json
import os
import sys

import requests

API_URL = "https://api.perplexity.ai/v1/agent"

def stream_answer(question: str) -> None:
    api_key = os.environ["PERPLEXITY_API_KEY"]
    payload = {
        "model": "perplexity/sonar",
        "input": question,
        "max_output_tokens": 250,
        "tools": [{"type": "web_search"}],
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with requests.post(API_URL, headers=headers, json=payload, stream=True, timeout=120) as response:
        response.raise_for_status()
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8")
            if not line.startswith("data: "):
                continue
            event = json.loads(line[len("data: "):])
            if event["type"] == "response.output_text.delta":
                print(event["delta"], end="", flush=True)
            elif event["type"] == "response.completed":
                break
            elif event["type"] == "response.incomplete":
                print("\n[truncated: max_output_tokens reached]", file=sys.stderr)
                break
            elif event["type"] in ("response.failed", "response.cancelled", "error"):
                raise RuntimeError(f"stream ended: {event['type']}")
    print()

def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else "Why is the sky blue?"
    stream_answer(question)

if __name__ == "__main__":
    main()
