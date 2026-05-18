# Threat model

This document expands on [SECURITY.md](../SECURITY.md) for readers
interested in the design rationale. The TL;DR lives in `SECURITY.md` —
this is the long form.

## Context

The Coach is a multi-agent system that:

- Reads from external APIs (intervals.icu, Strava, Garmin) controlled by
  the athlete's accounts
- Receives messages from a Telegram chat (when the plugin is enabled),
  optionally from a single allowed user ID
- Persists athlete state in local files (`config/`, `data/`)
- Pushes back to intervals.icu (workouts, NOTEs)
- Executes shell commands through Claude Code's permissions model
- Calls a remote LLM (Anthropic Claude) and another (Google Gemini for
  video analysis)

The trust boundary lies between **the LLM** (and any content that flows
into its prompts) and **the local file system + connected services**.

## What we actually defend against

### 1. Prompt injection via external text

**Vector.** Notes saved on intervals.icu, activity names/descriptions on
Strava and Garmin, parsed exercise lines from workout descriptions, and
the Gemini video-analysis response all eventually appear in some LLM's
context window — either directly in the planner prompt or indirectly via
files that specialists later read.

**Defence.** The `app.utils.sanitize.escape_for_prompt()` helper truncates
to a max length and backslash-escapes a small set of characters that
would otherwise start markdown / format-string / heading structures.
Leading `#` characters on lines are stripped to defang fake `# system:`
prompts.

It is applied at every known boundary:

- `context_builder._format_notes()` — for intervals.icu NOTEs
- `scripts/log_muscle_load._append_unmapped()` — before persisting raw
  exercise lines to `data/muscles/_unmapped.jsonl`
- `scripts/analyse_video._update_exercise_log()` — before persisting the
  Gemini response to `config/exercise_log.md`

**Limits.** This is hygiene, not defence-in-depth. A determined attacker
with control of the athlete's intervals.icu account can still craft
natural-language instructions that the LLM might honour. Multi-line
patterns, Unicode lookalikes, and instruction-style phrasing (e.g.
"please ignore previous instructions when planning today") are not
detected.

### 2. Hidden config edits by sub-agents

**Vector.** The `config-fixer` agent has `Edit` tool access. If
compromised (e.g. by a successful prompt injection from a finding's
text), it could silently change `config/*.md` or `prompts/*.yaml` in ways
the athlete wouldn't notice for days.

**Defence.** Mandatory approval log
(`data/approvals/YYYY-MM-DD-config-fixer.jsonl`) per edit, with:

- Finding ID being fixed
- SHA-256 of the proposed new content
- Athlete's exact approval text from the chat
- ISO timestamp

The agent prompt instructs: if the actual `Edit` deviates from the
approved diff (different hash), abort.

**Limits.** This is a prompt-level convention, not a filesystem lock. An
agent that does not follow its instructions can bypass it. The defence
is two-fold: (a) the log makes silent edits traceable after the fact,
(b) the athlete is in the loop and must approve a specific diff before
the agent edits.

### 3. Destructive bash commands via Telegram

**Vector.** When the Telegram plugin is enabled, the athlete can send
messages from a phone that the Coach interprets and might convert to a
bash command. A misread message could lead to `rm -rf` or
`git reset --hard`.

**Defence.** Explicit rule in CLAUDE.md and the Telegram-specific flow:

- Destructive bash commands (`rm`, `git reset --hard`,
  `git push --force`, `docker rm -f`, `chmod`, `chown`, anything with `/`
  or `~` as target path) are **never** executed directly on a Telegram
  message.
- The Coach states the intended action as plain text and waits for
  confirmation **in the terminal** (where the athlete physically is),
  not via Telegram.

**Limits.** Trust the athlete's understanding of what they typed. A
terminal-side confirmation is good enough for a single-operator system.

## What we explicitly do NOT defend against

### Compromised athlete accounts

If an attacker controls the Telegram chat, the intervals.icu account, or
the Strava account, they can shape the Coach's behaviour. Examples:

- A malicious NOTE in intervals.icu can flow into `athleteFeedback` and
  influence the planner. Sanitization stops the most common payloads but
  not natural-language injections.
- A modified Strava activity name can mislead the post-activity analyst.
- A spoofed Telegram message from the allowed user ID can drive
  arbitrary requests.

We assume authenticated channels are operator-controlled. This is a
hard limit of the design.

### Compromised Claude setup

The Coach trusts:

- Claude Code's permissions enforcement
- The Anthropic model behaving as instructed by its system prompt
- The agent definitions in `.claude/agents/`
- Plugins installed in the Claude Code environment

If any of these are compromised (tampered settings, malicious plugin,
unauthorised model change), the threat model breaks down.

### Active adversaries

The sanitization layer is hygiene against accidental or low-effort
injection. It is not defence-in-depth against a motivated attacker. The
project does not perform regular security testing, does not have a bug
bounty, and the author is not a security researcher.

### Data exfiltration through the LLM

Athlete configurations (body weight, injuries, PRs, competition plans) are
injected directly into prompts and therefore visible to the LLM provider
(Anthropic, Google Gemini, optionally LangSmith).

If LLM-provider data flow is a concern:

- Disable LangSmith tracing (`TRACE_TO_LANGSMITH=false`)
- Use a local-only model if you wire one up (not currently supported)
- Treat your athlete data as data the LLM provider will see

### Supply chain

Dependencies (intervals.icu client, pydantic, requests, gemini SDK, etc.)
are not regularly audited. `pyproject.toml` pins major versions but not
fully. Pull from upstream only what you trust.

## How a security issue would be handled

1. Reporter opens a GitHub issue (or emails
   [info@tobiaszander.de](mailto:info@tobiaszander.de)).
2. Maintainer triages within ~1 week (best effort — personal project).
3. If valid, a fix is pushed to `master` with an explanatory commit
   message (the git log is the change history).
4. The maintainer announces the fix in the relevant GitHub release.

There is no embargo, no CVE process, no coordinated disclosure. This is a
personal experiment, not a maintained product.
