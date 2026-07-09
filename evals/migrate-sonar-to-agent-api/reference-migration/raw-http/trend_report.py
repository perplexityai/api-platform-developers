import os
import sys

import requests

API_URL = "https://api.perplexity.ai/v1/agent"
MODEL = "perplexity/sonar"

RELATED_QUESTIONS_MARKER = "Related questions:"

def build_payload(topic: str) -> dict:
    return {
        "model": MODEL,
        "input": [
            {
                "role": "system",
                "content": (
                    "You are a concise tech analyst. Answer in 3-5 sentences. "
                    f'End with a section titled "{RELATED_QUESTIONS_MARKER}" '
                    "listing 3 short follow-up questions."
                ),
            },
            {
                "role": "user",
                "content": f"What are the most notable recent developments in {topic}?",
            },
        ],
        "max_output_tokens": 300,
        "temperature": 0.2,
        "tools": [
            {
                "type": "web_search",
                "filters": {
                    "search_recency_filter": "month",
                    "search_domain_filter": ["arstechnica.com", "theverge.com", "reuters.com"],
                },
            }
        ],
        "tool_choice": {"type": "web_search"},
    }

def fetch_report(topic: str) -> dict:
    api_key = os.environ["PERPLEXITY_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(API_URL, headers=headers, json=build_payload(topic), timeout=120)
    response.raise_for_status()
    return response.json()

def render(result: dict) -> None:
    if result.get("status") in ("failed", "cancelled"):
        raise RuntimeError(result.get("error"))
    if result.get("status") == "incomplete":
        print("warning: response truncated (max_output_tokens); rendering partial output", file=sys.stderr)

    answer = "".join(
        part["text"]
        for item in result["output"]
        if item["type"] == "message"
        for part in item["content"]
        if part["type"] == "output_text"
    )

    related: list[str] = []
    if RELATED_QUESTIONS_MARKER in answer:
        answer, _, tail = answer.partition(RELATED_QUESTIONS_MARKER)
        answer = answer.rstrip()
        related = [(line[2:] if line.startswith(("- ", "* ")) else line).strip() for line in tail.strip().splitlines() if line.strip()]

    print(answer)

    search_results = next(
        (item["results"] for item in result["output"] if item["type"] == "search_results"),
        [],
    )
    if search_results:
        print("\nSources:")
        for i, source in enumerate(search_results, 1):
            print(f"  [{i}] {source['url']}")
        print(f"\nTop result: {search_results[0]['title']} ({search_results[0]['url']})")

    if related:
        print("\nPeople also ask:")
        for q in related[:3]:
            print(f"  - {q}")

    usage = result.get("usage", {})
    print(f"\n[{result.get('model')}] tokens: {usage.get('input_tokens')} in / {usage.get('output_tokens')} out")

def main() -> None:
    topic = sys.argv[1] if len(sys.argv) > 1 else "quantum computing"
    print(f"Researching: {topic}\n")
    render(fetch_report(topic))

if __name__ == "__main__":
    main()
