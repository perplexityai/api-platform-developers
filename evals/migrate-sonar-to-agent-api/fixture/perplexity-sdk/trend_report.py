import sys

from perplexity import Perplexity

MODEL = "sonar-pro"


def fetch_report(client, topic):
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a concise tech analyst. Answer in 3-5 sentences."},
            {"role": "user", "content": f"What are the most notable recent developments in {topic}?"},
        ],
        max_tokens=300,
        temperature=0.2,
        search_recency_filter="month",
        search_domain_filter=["arstechnica.com", "theverge.com", "reuters.com"],
        return_related_questions=True,
    )


def render(completion):
    print(completion.choices[0].message.content)

    citations = completion.citations or []
    if citations:
        print("\nSources:")
        for i, url in enumerate(citations, 1):
            print(f"  [{i}] {url}")

    search_results = completion.search_results or []
    if search_results:
        print(f"\nTop result: {search_results[0].title} ({search_results[0].url})")

    related = completion.related_questions or []
    if related:
        print("\nPeople also ask:")
        for q in related[:3]:
            print(f"  - {q}")

    usage = completion.usage
    print(f"\n[{completion.model}] tokens: {usage.prompt_tokens} in / {usage.completion_tokens} out")


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "quantum computing"
    print(f"Researching: {topic}\n")
    client = Perplexity()
    render(fetch_report(client, topic))


if __name__ == "__main__":
    main()
