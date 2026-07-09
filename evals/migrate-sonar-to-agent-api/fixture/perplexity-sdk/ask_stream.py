import sys

from perplexity import Perplexity


def stream_answer(question):
    client = Perplexity()
    stream = client.chat.completions.create(
        model="sonar",
        messages=[{"role": "user", "content": question}],
        max_tokens=250,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            print(delta.content, end="", flush=True)
    print()


def main():
    question = sys.argv[1] if len(sys.argv) > 1 else "Why is the sky blue?"
    stream_answer(question)


if __name__ == "__main__":
    main()
