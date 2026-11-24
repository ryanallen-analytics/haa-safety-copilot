# haa-safety-copilot
![CI](https://github.com/ryanallen-analytics/haa-safety-copilot/actions/workflows/ci.yml/badge.svg)

"""Unit conversions used in flight planning."""

SM_TO_NM = 0.868976


def statute_to_nautical_miles(statute_miles: float) -> float:
    """Convert statute miles to nautical miles."""
    return statute_miles * SM_TO_NM

## Architecture (Phase 1 sketch)

```mermaid
flowchart TD
    A[Mission request: type, route, time] --> R{Code routes by mission type}
    R --> K[Checklist: route items +<br/>day/night and IFR/VFR layers]
    R --> W[Weather agent<br/>METAR, TAF, PIREP, SIGMET; step limit]
    R --> G[Regulations retrieval]
    R --> H[Accident history retrieval]
    W --> V[Code: validate results with parse_metar,<br/>set threshold flags]
    V --> M[Merge sections<br/>failed section shown as a gap]
    G --> M
    H --> M
    M --> D[Draft briefing with citations]
    K --> D
    D --> C{Code: citations present?<br/>flag go/no-go wording}
    C -->|missing citations| D
    C -->|passes| J{LLM judge, 3 votes:<br/>checklist covered?<br/>no go/no-go recommendation?}
    K --> J
    J -->|2 of 3 fail| D
    J -->|passes| P[Pilot reviews and decides]
    C -.->|after 2 revisions,<br/>issues flagged| P
    J -.->|after 2 revisions,<br/>issues flagged| P
```

An agent inside a fixed workflow. Code routes on the mission type the
pilot enters, which selects a checklist. The three research sections run
in parallel; a section that fails appears in the briefing as a visible gap.
The weather section is the only agent: it chooses which stations and
products to check, within a step limit, and code validates every result
and sets hazard flags from fixed thresholds. The draft passes code checks
for citations, which also flag go/no-go wording, then an LLM judge that
votes three times on checklist coverage and on whether the briefing
recommends go or no-go. Revisions are capped at two; a draft that still
fails reaches the pilot with its issues flagged. The pilot in command
makes every go/no-go decision.