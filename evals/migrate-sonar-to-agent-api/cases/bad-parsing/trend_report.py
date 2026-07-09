import os
import sys

import requests

API_URL = "https://api.perplexity.ai/v1/agent"
MODEL = "perplexity/sonar"


def build_payload(topic):
    return {
        "model": MODEL,
        "instructions": "You are a concise tech analyst. Answer in 3-5 sentences.",
        "input": f"What are the most notable recent developments in {topic}?",
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
    }


def fetch_report(topic):
    api_key = os.environ["PERPLEXITY_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(API_URL, headers=headers, json=build_payload(topic), timeout=120)
    response.raise_for_status()
    return response.json()


def render(result):
    last_item = result["output"][-1]
    answer = last_item["content"][0]["text"]
    print(answer)

    citations = result.get("citations", [])
    if citations:
        print("\nSources:")
        for i, url in enumerate(citations, 1):
            print(f"  [{i}] {url}")
    else:
        print("\nSources: (none returned?)")


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "quantum computing"
    print(f"Researching: {topic}\n")
    render(fetch_report(topic))


if __name__ == "__main__":
    main()
