# Choose Your Mystery

**An AI-powered social murder mystery party game**, built as a Godot 4 client talking to a
Python FastAPI backend. Players join a lobby, investigate a generated crime, interrogate AI
suspects, share clues, and race to accuse the killer.

You describe a setting — a 1920s jazz club, a Scottish castle, a corporate retreat — and the
backend generates a complete, coherent murder mystery: victim, suspects, motives, alibis,
physical evidence, and a hidden culprit, drawn from a corpus of classic mystery literature.
Every mystery passes an automated coherence check before the game begins.

**Core mechanic:** each player must share 75% of what they learn — forcing collaboration while
preserving individual advantage.

---

## Status

Godot migration, **Phase 3d** (lobby flow, room codes, multiplayer game start). See `CLAUDE.md`
for the full architecture and `SESSIONS.md` for session-by-session history.

> **This project was originally a single-player Streamlit app hosted on HuggingFace Spaces.**
> That version is retired — all of it is archived under [`deprecated/`](deprecated/) for
> historical reference, not for use. Everything below describes the current Godot + FastAPI
> version.

---

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r server/requirements.txt
python3 -m uvicorn server.main:app --port 8000
```

Then open `godot/project.godot` in Godot 4 — **Edit, not Run**, on a fresh clone — and press F5.

**An API key is only needed to GENERATE a mystery.** Playing one that is already in
`mystery_database/generated/` costs nothing and needs no key at all, because APF makes no play-time
API calls. Set `ANTHROPIC_API_KEY` when you want to generate:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**Use `python3 -m uvicorn`, not bare `uvicorn`.** The launcher script is missing from `PATH` on
Homebrew Python, on `pip install --user`, and in any terminal where the venv is not active; the
`-m` form works whenever the package is importable.

Requires [Godot 4](https://godotengine.org).

---

## For developers

| File | Purpose |
|---|---|
| `server/main.py` | FastAPI backend — all AI endpoints |
| `godot/` | Godot 4 client (scenes + GDScript) |
| `part_registry.py` | 1,469-part corpus; sampling logic |
| `coherence_validator.py` | P1 causal-chain validator (zero API calls) |
| `localization.py` | Era-appropriate name/occupation localization |
| `extraction_protocols.py` + `scripts/extract_from_pdfs.py` | Adding new corpus sources |
| `docs/WIRING.md` | Full technical architecture |
| `CLAUDE.md` | Instructions for AI coding assistants |
| `deprecated/` | Retired Streamlit/HuggingFace-era code — history only |

---

## License

Codebase: MIT. Mystery source texts: public domain (Project Gutenberg, pre-1928).
Generated mysteries: verify AI provider terms before commercial use.
