# wrapper.example/ — consumer wrapper skeleton

A minimal scaffold for a private wrapper repo around the
[aicoach-framework](https://github.com/airbone42/360-data-athlete)
plugin. Copy or fork this directory's contents into a new private repo
to start, then fill in your athlete-specific files.

## Why a wrapper

The plugin lives read-only under `~/.claude/plugins/...` once you run
`/plugin install aicoach-framework@360-data-athlete`. Your athlete data
— configs, credentials, runtime artefacts, your personal coaching
rules — lives in a separate **wrapper repo** you keep private. The
plugin's `app/utils/paths.py` loader looks for `config/` in your
wrapper first and falls back to the plugin's `config.example/` defaults
file by file, so anything you don't override keeps working out of the
box.

## Quickstart

1. **Copy this directory into a new private repo:**

   ```bash
   gh repo create my-athlete --private --clone
   cp -r ~/.claude/plugins/marketplaces/360-data-athlete/aicoach-framework/wrapper.example/. my-athlete/
   cd my-athlete
   ```

2. **Fill in your athlete configs.** Copy any file from the plugin's
   `config.example/` into `config/` and edit it. Files you do not copy
   fall back to the plugin defaults automatically.

   ```bash
   cp ~/.claude/plugins/marketplaces/360-data-athlete/aicoach-framework/config.example/athlete_static.md config/
   cp ~/.claude/plugins/marketplaces/360-data-athlete/aicoach-framework/config.example/athlete_status.md config/
   cp ~/.claude/plugins/marketplaces/360-data-athlete/aicoach-framework/config.example/athlete_preferences.md config/
   ```

3. **Fill `.env`** with the credentials you have. The full template
   with all variables lives at
   `~/.claude/plugins/marketplaces/360-data-athlete/aicoach-framework/.env.example`.

4. **Edit `CLAUDE.md`** to capture your personal coaching rules,
   restrictions, and language preference. This is your wrapper's
   project-level CLAUDE.md — it loads on top of the plugin's
   framework-level CLAUDE.md.

## What goes where

| Path | Sphere | Edit freely |
|------|--------|-------------|
| `~/.claude/plugins/.../aicoach-framework/` | Framework (public, read-only) | No — open a PR upstream instead |
| `config/` (this repo) | Personal | Yes |
| `.env` (this repo) | Personal — gitignored | Yes |
| `CLAUDE.md` (this repo) | Personal | Yes |
| `data/` (this repo) | Personal runtime artefacts | Yes |
| `.claude/settings.json` (this repo) | Personal — plugin enablement, hooks | Yes |

## Contributing back

Generic improvements — new validator rules, agent fixes, new training
paradigms applicable to any athlete, documentation clarifications,
bug fixes with reproductions — belong **upstream**. Open a PR against
[airbone42/360-data-athlete](https://github.com/airbone42/360-data-athlete).
See the framework's `CONTRIBUTING.md` for what makes a mergeable PR.

Athlete-specific edits (your PRs, your zones, your injuries, your
equipment, your language) stay in this wrapper. Never edit the plugin
install directory directly.
