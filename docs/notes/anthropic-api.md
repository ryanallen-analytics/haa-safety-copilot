# Anthropic API notes (2026-11-06)

1. The API is stateless: every request resends the full conversation. System
   instructions go in the top-level `system` parameter, not a message role.
2. temperature/top_p/top_k were removed in API version 2026-10-21 (400 error).
   Behavior is shaped by prompting; tutorials that set temperature=0 are stale.
3. Default sampling varies wording but not substance across runs, so evals need
   multiple runs per question and meaning-based grading.
4. System prompts work and cost tokens on every call: mine added ~38 input
   tokens and moved the go/no-go decision to the pilot in command.
5. Truncation is silent in the text; only stop_reason == "max_tokens" reveals it,
   so the client must log stop_reason.

Haiku 5.5 pricing: $0.10 / M input tokens, $0.50 / M output tokens

Eval candidates:
- Go/no-go framing (seen in 2 of 3 runs without a system prompt)
- Patient condition listed as a risk factor; verify against AC 135-14B