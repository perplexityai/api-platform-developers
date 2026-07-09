import json
import os
import sys

import requests

API_URL = "https://api.perplexity.ai/chat/completions"

def stream_answer(question: str) -> None:
    api_key = os.environ["PERPLEXITY_API_KEY"]
    payload = {
        "model": "sonar",
        "messages": [{"role": "user", "content": question}],
        "max_tokens": 250,
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
            data = line[len("data: "):]
            if data.strip() == "[DONE]":
                break
            chunk = json.loads(data)
            delta = chunk["choices"][0]["delta"].get("content")
            if delta:
                print(delta, end="", flush=True)
    print()

def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else "Why is the sky blue?"
    stream_answer(question)

if __name__ == "__main__":
    main()
