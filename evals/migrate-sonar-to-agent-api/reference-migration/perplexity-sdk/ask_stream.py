import sys

from perplexity import Perplexity


def stream_answer(question):
    client = Perplexity()
    stream = client.responses.create(
        model="perplexity/sonar",
        input=question,
        tools=[{"type": "web_search"}],
        max_output_tokens=250,
        stream=True,
    )
    for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)
        elif event.type == "response.completed":
            break
        elif event.type in ("response.failed", "response.incomplete", "response.cancelled", "error"):
            raise RuntimeError(f"stream ended: {event.type}")
    print()


def main():
    question = sys.argv[1] if len(sys.argv) > 1 else "Why is the sky blue?"
    stream_answer(question)


if __name__ == "__main__":
    main()
