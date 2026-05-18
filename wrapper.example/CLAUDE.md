# <Your athlete name> — wrapper for aicoach-framework

This is your private wrapper around the
[aicoach-framework](https://github.com/airbone42/360-data-athlete)
plugin. Rules and files here override or extend the framework defaults
for your specific situation.

## What lives where

| Location | Content |
|----------|---------|
| `~/.claude/plugins/.../aicoach-framework/` | Plugin code — read-only, do not edit |
| `config/` (this repo) | Your athlete data — overrides plugin defaults |
| `.env` (this repo) | Your credentials — gitignored |
| `CLAUDE.md` (this file) | Your personal coaching rules |
| `data/` (this repo) | Runtime artefacts (muscle log, audits, approvals) |
| `.claude/settings.json` (this repo) | Plugin enablement, hooks |

## Personal vs. framework

Everything you put in this repo is **personal** — names, PRs, injuries,
restrictions, equipment, language, incident anchors. None of that
belongs in the plugin install directory.

If you find a bug or want a generic improvement (a new validator rule,
a new agent, a corrected paradigm, a documentation fix), open a PR
against
[airbone42/360-data-athlete](https://github.com/airbone42/360-data-athlete).
See the framework's `CONTRIBUTING.md` for what kind of PR is likely to
land.

Athlete-specific tweaks stay here. Never edit the plugin install
directory directly — your edits would be wiped on the next
`/plugin update`.

## Language

Default coach response language is English. Override per-athlete in
`config/athlete_preferences.md` (`Coach response language: <code>`).

## Add your own rules below

Personal coaching rules, restrictions, incident anchors, equipment
quirks, scheduling preferences, polar-H10 wearing rules, business-trip
mode, recovery-week wording — anything that is specific to you and that
the coach should respect on top of the framework defaults.

… your rules here …
