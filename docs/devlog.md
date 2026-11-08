# Devlog

## 2026-10-28/29 · Week 0: project setup

**What I set up**
- uv package (`src/` layout) with pytest and ruff; first function and test passing
- `.env` / `.env.example` for the API key, verified ignored with `git check-ignore`
- `scripts/hello_llm.py`: one call to claude-haiku-5-5, 41 input / 144 output tokens

**What confused me**
- Ran `uv init` one folder above the git repo, so project files were outside version control
- Moved the repo out of OneDrive; a stray workspace config still pointed at the old path
- First test imported a tutorial module (`tiny_project`) that didn't exist
- Commits failed until I set `user.name` and `user.email` in git
- Put my real key in `.env.example`; GitHub push protection blocked the push, so I
  rebuilt the commits with `git reset --soft` and kept placeholders in the example file

**What I noticed**
- The model called the risk analysis a "go/no-go decision tool". My system must never
  make that call, so this framing goes on the eval list

**What's next**
- Build `llm_client.py` that logs model, tokens, latency, and cost for every call

## 2026-11-06/07 · LLMClient and fake-client tests (Week 0 complete)

- src/haa_safety_copilot/llm_client.py: LLMClient.complete() returns an LLMResponse and appends a JSONL record to logs/llm_calls.jsonl. First real call: 41 in / 163 out tokens, 1.88 s, $0.0000856.
- hello_llm.py now goes through LLMClient. tests/test_llm_client.py: two tests with a fake Anthropic client (records calls, no network) using tmp_path. They cover the cost math, passing system through, the log line, max_tokens truncation, and None cost for unknown models.

*** Problems and fixes ***

- pytest collected only 2 tests: tests/test_units.py had lost its test function. Restored it; 3 passing.

*** Lessons ***

- Dependency injection (passing the client in) is what makes the code testable without the network. Read the "collected N items" line, not just "passed".

*** Why I used a fake client to test LLMClient ***
I inject the LLM client so unit tests can use a fake. That keeps them free, fast, and deterministic, and lets me test edge cases like truncation. A separate real call checks that the integration works.

