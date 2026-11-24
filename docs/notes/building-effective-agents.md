# Building effective agents: notes (2026-11-10)

## Core distinction
- A workflow follows a path I write in code, and the LLM fills in steps. An agent picks its own next step and tools in a loop. Agents are more flexible but slower, costlier, and harder to predict, so use them only where the path can't be known ahead of time.
- `parse_metar` is a workflow: the path is fixed in code, and code (not the model) decides whether to retry. It's also a small evaluator-optimizer loop where the evaluator is Pydantic rather than an LLM.

## Patterns mapped to the HAA copilot
- **Prompt chaining:** each step's output feeds the next, with code checks in between. `parse_metar` sends a raw METAR plus the `WeatherSummary` schema and the month/year to the LLM, strips code fences, and validates with Pydantic; on failure it retries once with the errors, then raises `MetarParseError`. The next link should be code, not the model: compare the validated weather against fixed minimums and set flags like "low ceiling" from thresholds. That fixes the inconsistent `hazards` field.
- **Routing:** route on mission type, scene response vs interfacility transfer, since every mission is exactly one. The pilot supplies the mission type, so plain code routes it; no LLM classifier needed. Day/night and IFR/VFR combine (a night IFR scene flight), so they're layered checklist items within each route, not separate routes.
- **Parallelization**, two variants:
  - *Sectioning:* weather, regulations, and accident history run as separate calls at the same time. Code merges them into fixed briefing sections in a set order, each keeping its own citations. If a section fails or times out, the briefing shows it as a visible gap (e.g. "Accident history: not available"), never a silent omission; the pilot needs to know what wasn't checked.
  - *Voting:* run the same task several times and compare. My API experiments showed identical prompts give different wording, so one run shouldn't decide pass/fail. The LLM judge runs 3 times and fails a draft only when the runs agree (at least 2 of 3).
- **Orchestrator-workers:** best when subtasks can't be predicted. Mine are predictable and predefined, so I likely won't use it.
- **Evaluator-optimizer:** check each draft briefing in two layers.
  1. *Code (cheap, deterministic):* every claim carries a citation; a keyword pass flags go/no-go wording. The flag alone doesn't fail a draft, because "the final go/no-go decision remains with the pilot in command" is exactly the framing I want, and a phrase ban would reject it.
  2. *LLM judge (3 votes):* every checklist category is covered, and the briefing never states or implies a recommendation to go or not go, looking closely at any flagged phrases.

  The drafting call revises from the feedback, capped at two rounds; a draft that still fails goes to the pilot with its issues flagged. The judge needs its own eval cases (drafts with a missing category, a subtle recommendation, and the acceptable "decision remains with the PIC" framing), or I won't know whether it can be trusted.

## Design decisions this changes
- **An agent inside a workflow.** The backbone stays fixed: parallel research sections → draft → checks → pilot.
- **The weather section is the agent.** Which stations along the route matter, whether a TAF or PIREP needs checking, and whether a SIGMET applies can't be fixed in advance, so a small agent with a step limit decides. That's the real job for the hand-built loop in Weeks 2–3; code still validates every tool result and sets the threshold flags.

## Also worth noting
- **Augmented LLM:** the building block is an LLM with retrieval, tools, and memory; Phase 2 adds retrieval, Week 3 adds tools.
- **Tool design:** treat tool descriptions and inputs as carefully as a prompt: clear names, examples, edge cases, and input formats that are hard to get wrong.
- **Stopping conditions:** agents need a step limit and checkpoints for human review, or they can loop and run up cost.
- **Frameworks:** start with the API directly so I understand the loop; frameworks add abstraction that can hide prompts and responses. Matches building by hand in Phase 1 before LangGraph in Phase 3.