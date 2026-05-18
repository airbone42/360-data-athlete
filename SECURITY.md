# Security

This is an **experimental** project. The threat model below describes what
the framework does and does not defend against. Read it before exposing
the system to data you care about.

## Threat model

### What we defend against (best-effort)

| Threat | Mitigation |
|--------|------------|
| Prompt injection via athlete notes from intervals.icu | `app.utils.sanitize.escape_for_prompt()` at the `_format_notes` and `_format_events` boundaries in `context_builder` |
| Prompt injection via Strava / Garmin activity names and descriptions | Sanitized at every write boundary that lands in a prompt: `_summarize_activity` (`name`, `coaching_notes`), `_summarize_today_workouts` (`name`), and `history_fetcher._format_activity` (`name`, `description`, message `content`) |
| Prompt injection via third-party weather descriptions | OpenWeather `description` text is sanitized in `_build_weather_info` before it flows into the planner context as `weatherInfo` (defense-in-depth — small attack surface, but cost is zero) |
| Prompt injection via auto-surfaced drift findings (`configDrift`) | `evidence` strings produced by `check_log_vs_history` carry Activity-Description-derived text and are sanitized in `fetch_context.py` before being attached to the planner context, so a Strava-roundtrip-injected exercise line cannot break the planner prompt |
| Prompt injection via parsed exercise lines in workout descriptions | `escape_for_prompt()` applied before persisting to `data/muscles/_unmapped.jsonl` (which can later be loaded into a review context) |
| Prompt injection via Gemini video-analysis output | `escape_for_prompt()` applied before writing to `config/exercise_log.md` |
| Hidden / un-audited config edits by `config-fixer` | Mandatory approval log (`data/approvals/YYYY-MM-DD-config-fixer.jsonl`) per edit, with finding ID + diff hash + athlete approval text |
| Accidental destructive bash commands from Telegram | `CLAUDE.md` rule: destructive bash commands (`rm`, `git reset --hard`, force push, `docker rm -f`, etc.) require terminal confirmation, never Telegram-only |

### What we explicitly do NOT defend against

- **Compromised athlete accounts.** If an attacker controls the Telegram
  bot, the intervals.icu account, or the Strava account, they can push
  the Coach in arbitrary directions. The Coach treats authenticated
  channels as authoritative.
- **Compromised Claude setup.** The Coach trusts Claude Code's
  permissions enforcement and the underlying model. Settings file
  tampering, plugin compromise, or malicious agent definitions are out of
  scope.
- **Active adversaries.** The sanitization layer is hygiene — it neutralises
  accidental or low-effort injection. It is not a defence-in-depth against
  a motivated attacker. Anyone with write access to your `config/` can
  reshape the Coach's behaviour.
- **Data exfiltration through the LLM.** Configs are loaded directly into
  prompts. Treat anything in `config/` as data the LLM provider sees.
- **Supply chain.** The framework pulls in pydantic, requests, gemini SDK,
  intervals.icu/Strava clients, etc. Dependency vulnerabilities are not
  tracked by this project.

### Why the sanitization is best-effort

`app/utils/sanitize.py:escape_for_prompt()` does four things:

1. Truncate to a maximum length (default 200 characters)
2. Backslash-escape characters that start markdown / format-string
   structures: `` ` ``, `{`, `}`, `<`, `>`
3. Strip leading `#` characters on each line (defang headings)
4. Pass through everything else verbatim

This stops the most common low-effort injections (Markdown code-fence
break-out, `{coaching_notes}` re-interpretation, fake `# system:` blocks).
It does **not** stop a determined attacker — multi-line patterns,
Unicode tricks, instruction-style natural-language phrasing, etc., are not
addressed.

## Operator responsibilities

You — the operator — are responsible for:

1. **Securing your credentials.** Don't commit `.env`. Don't paste tokens
   into chat. Rotate keys regularly. The `.gitignore` is configured for
   this, but it's not a guarantee.
2. **Trusting your athlete channels.** Only allow trusted Telegram chat IDs.
   The Coach trusts authenticated messages.
3. **Reviewing config-fixer edits.** The approval log captures every edit,
   but it is the operator's job to actually read it and revert if anything
   looks wrong.
4. **Auditing your prompt cache.** Tracing via LangSmith is optional and
   off by default. If you enable it, your prompts and athlete data flow
   to LangSmith — make sure that's acceptable for you.

## Reporting a security issue

- Preferred: open a GitHub issue with the `security` label.
- Sensitive disclosures: email
  [info@tobiaszander.de](mailto:info@tobiaszander.de).
- Expect a response within a week or so — this is a personal experiment,
  not a maintained product.

## What gets rotated on a credential leak

Even before a public release, if a credential was committed to git
history (private repo) it must be considered exposed and rotated. The
following are sensitive in this codebase:

- `INTERVALS_ICU_API_KEY` — intervals.icu API access
- `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REFRESH_TOKEN` —
  Strava OAuth
- `GARMIN_EMAIL`, `GARMIN_PASSWORD` — Garmin web scraping fallback
- `TELEGRAM_BOT_ACCESS_TOKEN` — Telegram bot
- `OPENROUTER_API_KEY` — model provider (Gemini and others, proxied via OpenRouter)
- `CC_LANGSMITH_API_KEY` — LangSmith tracing
- `TELEGRAM_ALLOWED_USER_IDS` — whitelist of authorised Telegram chat IDs

Rotation procedure: revoke at the provider, generate a new credential,
update `.env` and (if used) `.claude/settings.local.json`.
