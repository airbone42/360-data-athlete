# Contributing

Thanks for the interest. A few things to know up front.

## This is a personal experiment

The framework is maintained for the author's own training and as a
testbed for multi-agent architectures on top of Claude Code. There is
no roadmap, no SLA, and no commitment to accept contributions or
respond quickly. Wrapper-friendly is the design — see
[wrapper.example/](wrapper.example/) for how to build a private
athlete repo on top of this plugin without forking.

## Scope: framework vs. athlete data

`framework/` (this repo) is **athlete-agnostic** — code, generic rules,
generic agents, generic paradigms, framework defaults in
`config.example/`. Anything that names a specific athlete, embeds a
specific athlete's data (PRs, HR zones, LTHR, body weight,
equipment-brand quirks, injury history, incident dates), or hardcodes
a single athlete's preferences (language, business-trip mode,
scheduling rules) belongs in a **wrapper repo**, not here.

A generic rule that happens not to fit the maintainer's current
training is still in scope and welcome — for example a Masters-50+
recovery protocol, a swim-specific zone model, or a low-carb
periodisation paradigm. The rejection criterion is "athlete-specific
implementation detail leaking into framework", not "doesn't match the
maintainer's profile".

The nine concrete anti-patterns that prompted this scope rule — and
that any framework-edit must pass — are documented under
[CLAUDE.md](CLAUDE.md) ("Public-Cut-Disziplin" / Athleten-Agnostik-
Check). Read them once before your first PR.

## What contributions make sense

These are the kinds of changes most likely to be merged:

- **Bug fixes** with a clear reproduction and a regression test
- **English translations** of `config.example/` files still marked
  `TODO: translate` (the demo configs must read cleanly in English)
- **Documentation** that clarifies an existing concept (architecture,
  threat model, agent collaboration model, sport-science rationale)
- **Defensive hardening** in [app/utils/sanitize.py](app/utils/sanitize.py)
  or at a new prompt boundary, with a regression test
- **New validator rules** in [scripts/validate_plan.py](scripts/validate_plan.py)
  or the `plan-validator` agent, with example failing/passing plans
- **New agents or training paradigms** that apply to any athlete, with
  a backing research document under [research/](research/) following
  the schema in [research/README.md](research/README.md)
- **New tests** that pin down current behaviour

## What contributions are unlikely to land

- Anything embedding athlete-specific data (PRs, zones, injuries,
  incident dates, names, equipment brands, body weight) — that material
  belongs in a wrapper's `config/`, never in `framework/`. See
  [wrapper.example/](wrapper.example/) for the intended layout.
- New paradigms or scaling decisions without a research document
  under [research/](research/) — see CLAUDE.md →
  "Research-before-scaling-or-new-protocol"
- Large refactors of the agent system without a discussion first
- Feature requests that depend on services or formats the maintainer
  doesn't use (no roadmap, no triage capacity)
- Breaking changes to the config schema without a migration path
- Detection-evasion / opsec features — out of scope, see
  [SECURITY.md](SECURITY.md)

## Pre-submission checklist

Before opening a PR, run through this list. Most rejected PRs in the
past failed at least one of these:

- [ ] **Athlete-agnostic.** No specific PRs, HR/LTHR/zone values,
      body weight, injury history, equipment brands, athlete names, or
      dated incident anchors ("Vorfall 12.05.2026") in any
      framework-tracked file.
- [ ] **System prompts take athlete context via parameter**, not
      hardcoded. If your prompt references restrictions, sport profile,
      or injuries, those reach the prompt via `--context` / function
      argument / ENV — not via a hardcoded `SYSTEM_PROMPT = "..."`.
- [ ] **No hardcoded fallback IDs or maintainer paths.** Missing ENV /
      config returns `None` + a clear log line, not a maintainer
      default ID, chat ID, or absolute home directory.
- [ ] **`config.example/` carries clear / empty defaults**, not active
      restrictions or rehab states. A new wrapper user should start
      from an empty status block, not from the maintainer's injury
      list.
- [ ] **Boundary sanitisation.** Any new function that builds a prompt
      from external input (intervals.icu, Strava, Garmin, OpenWeather,
      athlete notes) routes the user-controlled fields through
      `app.utils.sanitize.escape_for_prompt(..., max_len=N)`.
- [ ] **Tests pass.** `pytest tests/` is green; new features carry new
      tests. Test fixtures with date strings use synthetic dates
      (e.g. 2025-pendants), not the real maintainer timeline.
- [ ] **Conventional Commit message** with scope when it helps
      (`fix(planner): …`, `feat(validator): …`). One concern per
      commit; no mixing of unrelated changes.
- [ ] **If introducing a new paradigm, scaling decision, or new
      exercise class:** a research document exists under
      [research/](research/) following
      [research/README.md](research/README.md), and the PR description
      references it.

## Style

- Python 3.11+, type hints everywhere, `from __future__ import annotations`
- No dead code, no leftover comments, no "added for issue #X" notes —
  keep the change focused and remove what you replace
- Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`)
  with a scope when it helps (`fix(planner): ...`)
- `pytest tests/` before submitting; new files need new tests

## Security

If you found a security issue (prompt-injection vector, secret leak in
logs, sanitisation bypass), please follow the disclosure path in
[SECURITY.md](SECURITY.md) instead of opening a public PR or issue.

## Code review

Reviews are async and may be terse. Don't read "merge after a clarification"
as enthusiasm — read it as practical engagement. If there is no engagement
within two weeks, assume the PR is on hold.

## Maintainer

[Tobias Zander](mailto:info@tobiaszander.de) · multi-sport athlete · AI
visionary. Reach me by email for non-trivial discussions; for code changes
prefer a PR.
