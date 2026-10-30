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