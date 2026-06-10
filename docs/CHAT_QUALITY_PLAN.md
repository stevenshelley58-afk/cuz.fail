# Chat Quality Rebuild Plan — `/api/v1/assistant`

Status: ready for implementation. Authority: subordinate to `docs/MASTER_REBUILD_PLAN.md` and CLAUDE.md governance (advisory-only outputs, cite approved source versions, deterministic for measurements).

## Problem statement

Current behavior (all in `src/draftcheck/api/sources.py`, `assistant_chat`, ~line 981):

1. **No relevance threshold.** `search_service.search_chunks(question, limit=6)` is lexical token-overlap. Any keyword collision returns a hit, so common words ("setback", "height") drag in barely-related chunks.
2. **Cite-all-retrieved.** `_dedupe_assistant_citations(hits)` returns every retrieved chunk as a citation, regardless of whether the model actually used it. The `[n]` markers the model writes are ignored.
3. **Binary routing.** `if hits:` → grounded prompt with all 6 chunks; else general prompt. One stray hit forces the grounded path; a general question gets buried in irrelevant extracts.
4. **No conversation history.** `AssistantPayload` is single-message, so the assistant re-asks for facts already given and can't hold a thread.
5. **No follow-up policy.** Neither prompt tells the model when to ask a clarifying question vs. just answer.

Target behavior:

- General question → concise general answer + at most 2–3 "further reading" citations.
- Specific question with sources → specific cited answer; figures/measurements stay deterministic per governance.
- Specific question missing a decisive fact (R-Code density, council, lot dimensions) → answer the general rule first, then ask exactly ONE follow-up at the end. Never ask a question whose answer doesn't change the response. Never re-ask something already in the conversation.
- Citations shown = citations the model actually used, plus nothing else.

---

## Phase 1 — Retrieval filtering (backend, no schema changes)

**Files:** `src/draftcheck/api/sources.py` (and read `search_service.search_chunks` implementation for score semantics before picking constants).

1. In `assistant_chat`, after retrieving hits, apply a two-part filter:
   - **Relative threshold:** drop hits scoring below `0.35 × top_score`.
   - **Absolute floor:** drop hits below a minimum score (calibrate against the lexical scorer — inspect real score distributions with a handful of queries against the seeded library before hardcoding; start around the score a 2-token overlap produces and tune).
   - Cap context at 5 chunks post-filter.
2. Add a module-level config block (`_ASSISTANT_MIN_SCORE`, `_ASSISTANT_RELATIVE_FLOOR`, `_ASSISTANT_MAX_CONTEXT_CHUNKS`) with env overrides (`DRAFTCHECK_ASSISTANT_*`) so tuning doesn't need redeploys of code.
3. Keep `/search/chunks` and `/search/ask` behavior unchanged — this filter is assistant-only.

**Acceptance:** a query like "hello what can you do" retrieves zero post-filter hits and takes the general path. A query "rear setback R20 single storey" keeps its top R-Codes chunks.

## Phase 2 — Citations = what the model used

**Files:** `src/draftcheck/api/sources.py`.

1. After `provider.complete(...)` returns the grounded answer, parse `[n]` markers with a regex (`\[(\d{1,2})\]`, also handle `[1, 2]` / `[1][2]` forms).
2. Build the returned `citations` list ONLY from hits whose index appears in the answer. Renumber sequentially (rewrite the answer's markers so `[3]` becomes `[1]` if it's the first cited) — keep a stable index→citation mapping in the response so the frontend can link inline markers to chips.
3. Edge cases:
   - Model cites nothing but hits existed → return the single top hit as citation and set `grounded: true` only if the answer plausibly drew on it; otherwise return `citations: []`, `grounded: false`, no disclaimer.
   - Model cites an index out of range → drop the marker, log a warning.
4. Response shape: add `citation_map: [{marker: 1, citation: {...}}]` alongside the existing `citations` array (keep `citations` for backward compat during the frontend transition).

**Acceptance:** unit tests in `tests/test_v3_api_shell.py` (or a new `tests/test_assistant_citations.py`): answer citing `[1]` and `[3]` of 5 hits returns exactly 2 citations, renumbered; answer citing nothing returns ≤1.

## Phase 3 — One unified prompt with mode instructions

Replace the hard `if hits:` prompt fork with one system prompt that handles both, since post-Phase-1 the hits that survive are actually relevant.

**New `_ASSISTANT_SYSTEM_PROMPT` (replaces both `_GROUNDED_SYSTEM_PROMPT` and `_GENERAL_SYSTEM_PROMPT` in the live-provider path):**

Core instructions to encode (wordsmith freely, keep all of these behaviors):

- Identity: LotFile's expert assistant for WA residential planning and design (R-Codes, local schemes, DA process, WAPC policy).
- **Match the question's altitude.** General question → short general answer; do not enumerate source extracts. Specific question → specific answer with the exact figures from SOURCES.
- **Cite selectively.** Cite `[n]` inline only for claims actually drawn from a source. Never list sources that weren't used. For a general answer, at most 2–3 citations as pointers, or none.
- **Figures discipline (governance):** never invent figures, clause numbers, or compliance outcomes not in SOURCES. A figure from general knowledge must be labeled "general knowledge — verify against approved source version". Never state a specific property/design is compliant or approved.
- **Follow-up policy:** Ask at most ONE clarifying question, only when the answer materially changes based on it (e.g., R-Code density, storeys, council/scheme), and only AFTER giving the best general answer you can. If the conversation already contains the fact, use it — do not re-ask. If no clarification would change the answer, ask nothing.
- **Length discipline:** default to concise. Headings/bullets only when the answer is long enough to need them. No boilerplate intro/outro.
- If SOURCES are present but irrelevant to the question, ignore them rather than forcing them in.

User-message construction: include SOURCES block only when post-filter hits exist (same `_assistant_source_context` format). When empty, send the question alone.

`grounded` in the response becomes "answer contains ≥1 used citation" (from Phase 2), not "retrieval returned anything". `disclaimer` only when grounded.

Keep the deterministic `search_service.ask` fallback path untouched (provider-down resilience), and keep `_GENERAL_FALLBACK_ANSWER` for the no-provider/no-hits corner.

**Acceptance:** see eval set in Phase 6.

## Phase 4 — Conversation history

**Files:** `src/draftcheck/api/sources.py` (AssistantPayload), `src/draftcheck/providers.py`, `web/src/api.ts`, `web/src/main.tsx`.

1. `AssistantPayload` gains `history: list[AssistantTurn] = []` where `AssistantTurn = {role: Literal["user","assistant"], content: str}`. Cap server-side: last 12 turns AND ~6,000 chars (truncate oldest first).
2. Extend the chat provider interface: `complete(system, user)` → add `complete_chat(system, messages)` (list of role/content dicts). Update the live provider in `providers.py` to pass messages through; keep `complete` as a wrapper for other call sites.
3. **Retrieval query rewriting:** when history exists, build the search query from the latest user message plus a lightweight concatenation of the previous user turn (cheap, no extra LLM call). This makes "what about two storeys?" retrieve correctly. (A proper LLM query-rewrite step is a later optimization — note it, don't build it now.)
4. Frontend: send the existing message list as `history` in `web/src/api.ts` assistant call; the SPA already holds messages in state in `main.tsx`.

**Acceptance:** turn 1 "I'm in R20, Stirling"; turn 2 "what's my rear setback?" → answer uses R20/Stirling, asks nothing.

## Phase 5 — Frontend citation rendering

**Files:** `web/src/main.tsx` (chat message rendering), `web/src/api.ts` (types).

1. Render chips from `citation_map` (fallback to `citations` if absent). Inline `[n]` markers in the markdown become superscript links that highlight/scroll to the matching chip.
2. Collapse chips: show up to 3 inline; more than 3 → "Sources (n)" expander. (Post-Phase-2 this should be rare.)
3. Show the disclaimer once per grounded answer as a muted footnote, not as a prominent banner per message.
4. No other UI redesign in this pass.

## Phase 6 — Eval gate (do not skip)

**Files:** new `tests/test_assistant_quality.py` + fixture `tests/fixtures/assistant_eval_set.json`.

Two layers:

1. **Deterministic unit tests** (no live provider — fake provider returning canned answers): threshold filtering, citation parsing/renumbering, history capping, payload shapes, `grounded` semantics.
2. **Behavioral eval set** (runs when a live provider key is present; skipped in CI otherwise, runnable manually pre-deploy). ~20 cases across four buckets, each with machine-checkable assertions:
   - *General* ("what are the R-Codes?", "how does a DA work in WA?") → assert `len(citations) <= 3`, answer contains no question mark in final paragraph.
   - *Specific, supported* ("minimum open space R30") → assert ≥1 citation, expected figure present.
   - *Specific, needs info* ("what's my side setback?") → assert exactly one question in the answer, and the answer also contains substantive content before it.
   - *Off-topic / chitchat* ("hi", "can you write me a poem") → assert 0 citations, no disclaimer.
3. Log per-case pass/fail; gate deploys on the deterministic layer in CI, run the behavioral layer manually and record results in the PR description.

## Sequencing & delivery

Implement in order 1 → 2 → 3 → 4 → 5 → 6, but write Phase 6's deterministic tests alongside each phase (TDD where cheap). Phases 1–3 are one PR (backend answer quality), Phase 4 a second PR (history, touches provider interface + frontend), Phase 5+remaining 6 a third. Per standing approval: commit, push, merge on green CI, deploy to the VPS per `docs/CODEX_DEPLOY_SYNC_RUNBOOK.md`. Do not touch Caddy/DNS/deployment architecture — same-origin `/api/v1` stays as is.

## Out of scope (note, don't build)

- Semantic/hybrid retrieval (embedding fields already exist on chunks — natural next step once behavior is right).
- LLM-based query rewriting for retrieval.
- Streaming responses.
- Per-council source scoping in chat.
