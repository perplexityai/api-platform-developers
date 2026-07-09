# Provenance

Produced by a real headless skill run (claude -p, sonnet, plugin loaded) on 2026-07-09, eval case 2.
That run shipped one live defect: `temperature=0.2` as a typed kwarg, which the SDK's `responses.create()` rejects at call time.
The eval caught it; the skill gained the typed-kwarg trap note in integration-styles.md, and this copy carries the one-line fix (`extra_body={"temperature": 0.2}`) applied per that guidance.
All three scripts were then live-verified against production and pass check.sh.
