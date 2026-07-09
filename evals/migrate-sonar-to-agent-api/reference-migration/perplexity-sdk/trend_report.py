import sys

from perplexity import Perplexity

MODEL = "perplexity/sonar"

RELATED_QUESTIONS_DELIMITER = "Related questions:"


def fetch_report(client, topic):
    instructions = "You are a concise tech analyst. Answer in 3-5 sentences."
    prompt = (
        f"What are the most notable recent developments in {topic}?\n\n"
        f'End with a section titled "{RELATED_QUESTIONS_DELIMITER}" listing 3 short follow-up questions.'
    )
    response = client.responses.create(
        model=MODEL,
        instructions=instructions,
        input=prompt,
        tools=[
            {
                "type": "web_search",
                "filters": {
                    "search_recency_filter": "month",
                    "search_domain_filter": ["arstechnica.com", "theverge.com", "reuters.com"],
                },
            }
        ],
        max_output_tokens=300,
        extra_body={"temperature": 0.2},
    )
    if response.status in ("failed", "cancelled"):
        raise RuntimeError(response.error or response.status)
    if response.status == "incomplete":
        print("warning: response truncated (max_output_tokens); rendering partial output", file=sys.stderr)
    return response


def render(response):
    answer, _, related_block = response.output_text.partition(RELATED_QUESTIONS_DELIMITER)
    print(answer.strip())

    search_results = next(
        (item.results for item in response.output if item.type == "search_results"),
        [],
    )
    if search_results:
        print("\nSources:")
        for i, result in enumerate(search_results, 1):
            print(f"  [{i}] {result.url}")
        print(f"\nTop result: {search_results[0].title} ({search_results[0].url})")

    if related_block.strip():
        related = [
            (line[2:] if line.startswith(("- ", "* ")) else line).strip()
            for line in related_block.strip().splitlines()
            if line.strip()
        ]
        if related:
            print("\nPeople also ask:")
            for q in related[:3]:
                print(f"  - {q}")

    usage = response.usage
    print(f"\n[{response.model}] tokens: {usage.input_tokens} in / {usage.output_tokens} out")


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "quantum computing"
    print(f"Researching: {topic}\n")
    client = Perplexity()
    render(fetch_report(client, topic))


if __name__ == "__main__":
    main()
