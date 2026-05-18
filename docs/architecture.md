# Architecture

## Distribution: Claude Code plugin

The framework is shipped as a Claude Code plugin named
`aicoach-framework`. The plugin manifest lives at
`.claude-plugin/plugin.json`; the marketplace entry that lets users
install it via `/plugin marketplace add` lives at
`.claude-plugin/marketplace.json`.

Agents and slash commands sit at the plugin root in `agents/` and
`commands/` and are auto-discovered by Claude Code — no need to enumerate
them in the manifest. When invoked, they are namespaced under the plugin
name: `aicoach-framework:<agent>` and `/aicoach-framework:<command>`.

**Override semantics.** A consumer who places a file at
`.claude/agents/<name>.md` in their own project gets a *project-level*
agent under the unqualified name `<name>`. The plugin's namespaced
agent (`aicoach-framework:<name>`) remains available in parallel — the
two coexist, they don't shadow each other. The same applies to slash
commands.

**Configuration-driven specialisation.** Plugin agents are intentionally
generic. They read athlete-specific facts (PRs, HR zones, restrictions,
language) from `config/` at runtime via `app.utils.prompt_loader`. The
canonical pattern for "I want this agent to behave differently for my
athlete" is therefore to edit `config/`, not to fork the agent.

## Layers

```
┌──────────────────────────────────────────────────────────────────┐
│  Interface — Claude Code (terminal | Telegram plugin)             │
├──────────────────────────────────────────────────────────────────┤
│  Plugin agents (agents/*.md)                                      │
│    head coach — CLAUDE.md driver, terminal/Telegram session        │
│    planner — strategic daily planner                              │
│    specialist-endurance / -complementary / -ninja                 │
│    coach-analyst / data-scientist                                 │
│    mental-coach / video-analyst                                   │
│    plan-validator (semantic)                                      │
│    config-auditor / config-fixer                                  │
│    physio-consultant / sports-ortho-consultant                    │
├──────────────────────────────────────────────────────────────────┤
│  Prompts (prompts/*.yaml)                                         │
│    model + temperature + template                                 │
│    template uses {config_key} placeholders — auto-substituted     │
│    from config/*.md by app.utils.prompt_loader                    │
├──────────────────────────────────────────────────────────────────┤
│  Domain logic (app/)                                              │
│    api/         — intervals.icu / Strava / Garmin clients         │
│    analytics/   — exercise parser, recovery rules                 │
│    graphs/      — context builder, type-history, workout parser   │
│    utils/       — paths, config loader, prompt loader, sanitize   │
├──────────────────────────────────────────────────────────────────┤
│  Scripts (scripts/*.py)                                           │
│    fetch_context, fetch_type_history, push_workouts,              │
│    delete_workouts, post_message, log_muscle_load,                │
│    muscle_overview, validate_plan, audit_consistency,             │
│    analyse_video, ...                                             │
├──────────────────────────────────────────────────────────────────┤
│  External services                                                │
│    intervals.icu (source of truth for activities + NOTEs)         │
│    Strava (gear, mirror of activities)                            │
│    Garmin (FIT files, running dynamics)                           │
│    Telegram (chat channel for athlete)                            │
│    Gemini API (video analysis)                                    │
│    LangSmith (optional tracing)                                   │
└──────────────────────────────────────────────────────────────────┘
```

## Path resolution (`app/utils/paths.py`)

The framework is designed to be embeddable as a submodule inside an
athlete-specific wrapper repository. Path resolution is the seam:

```python
FRAMEWORK_ROOT   = location of the framework code (this repo)
COACH_HOME       = the wrapper repo, defaults to FRAMEWORK_ROOT
CONFIG_DIR       = $COACH_HOME/config (overridable via $CONFIG_DIR)
DATA_DIR         = $COACH_HOME/data   (overridable via $DATA_DIR)
CACHE_DIR        = $COACH_HOME/cache  (overridable via $CACHE_DIR
                                       or $INTERVALS_CACHE_DIR)
PROMPTS_DIR      = $FRAMEWORK_ROOT/prompts (always framework-relative)
CONFIG_FALLBACK  = $FRAMEWORK_ROOT/config.example
```

`load_config(name)` looks in `CONFIG_DIR` first, then in `CONFIG_FALLBACK`.
That means: a standalone framework run with no `config/` falls back to
the **Alex Demo** profile in `config.example/`. A private wrapper repo
overrides individual files via `config/`, mixing demo defaults with
athlete-specific values.

## Two-repo layout (private wrapper + public framework)

```
aicoach-private/                          ← private repo (Gitea / similar)
├── .claude/
│   ├── settings.json                      enabledPlugins + extraKnownMarketplaces
│   ├── agents/                            (optional) project-level overrides
│   └── commands/                          (optional) athlete-specific commands
├── framework/                              public plugin (later: submodule)
│   ├── .claude-plugin/
│   │   ├── plugin.json
│   │   └── marketplace.json
│   ├── agents/                            13 generic sub-agents
│   ├── commands/                          6 slash commands
│   ├── app/, scripts/, prompts/, …
│   ├── config.example/                    defaults (Alex Demo)
│   └── CLAUDE.md                          generic, English
├── config/                                 athlete-specific
│   ├── athlete_static.md
│   ├── athlete_status.md
│   └── ...
├── data/                                   runtime — muscles, audits
├── cache/                                  (gitignored)
├── .env                                    (gitignored)
├── ATHLETE.md                              athlete-specific addendum (DE/EN)
└── .gitmodules
```

The wrapper's `.claude/settings.json` registers the framework as a local
marketplace via `extraKnownMarketplaces` and enables it in
`enabledPlugins`:

```json
{
  "extraKnownMarketplaces": {
    "360-data-athlete": {
      "source": { "source": "directory", "path": "./framework" }
    }
  },
  "enabledPlugins": {
    "aicoach-framework@360-data-athlete": true
  }
}
```

Claude Code loads local-path plugins **in place** — edits in
`framework/` take effect after `/reload-plugins` without any copy or
sync step. This keeps the dev loop identical to "one big repo" while
the boundary between wrapper and framework is enforced by the plugin
manifest.

Container deployments mount the wrapper as the working directory and
set `COACH_HOME=/wrapper-dir`. The framework code then reads configs
from `$COACH_HOME/config` and falls back to
`$COACH_HOME/framework/config.example` for anything missing. The
plugin registration in `.claude/settings.json` is independent of this
and stays unchanged when `framework/` later becomes a git submodule.

## Pane model

Agents are **not a pipeline**. They are pane-based teammates:

1. The head coach (session) drives.
2. For planning, the head coach starts the planner in a pane. The
   planner replies with a JSON directive.
3. The head coach reviews + adjusts in chat.
4. For each workout the head coach starts the right specialist
   (endurance / complementary / ninja) in a pane with a structured
   context: directive, type history, wellness, sibling workouts,
   warm-up de-duplication info.
5. After all specialists return, the head coach runs the plan validator
   (mechanical + semantic).
6. After the athlete confirms, `push_workouts.py` writes events to
   intervals.icu. The mechanical validator runs again as a last defence.

This shape — **head coach as the integrator**, specialists as fresh-context
teammates — keeps the surface area for cross-contamination small: each
specialist sees only what they need, not the full athlete history.

## Why this might be interesting

The interesting parts of this system are not the sport-science specifics —
they are the patterns that survived multiple iterations of pushback from
the maintainer (who is also the athlete):

- **Briefing rule**: the head coach gives specialists **state**, not
  **progression specifics**. Specialists derive the load from
  `config/exercise_progressions.md` and the type history themselves. This
  prevents the head coach's working memory from polluting the specialist's
  load decisions.
- **Warm-up de-duplication**: cross-workout consistency is enforced by
  the head coach during a review step. The mechanical validator is only
  a sanity net.
- **HR-zone briefing rule**: copy-paste from `context.hrZones` only,
  never from memory. The rationale is one specific incident
  (documented in `config/athlete_status.md`) where a memory-based briefing
  produced a Z3 ceiling for an easy run.
- **Consistency audit + auto-fix**: drift between configs, agents, and
  prompts is a real problem in long-lived multi-agent systems. The audit
  scanner + auditor agent + fixer agent (with approval log) is one
  approach to keep it manageable.
- **Approval log for config edits**: any agent with `Edit` access logs
  its intent before editing. Best-effort, but traceable.

## Where to start reading

If you're exploring the codebase:

1. [`CLAUDE.md`](../CLAUDE.md) — head-coach role + workflow rules
2. [`agents/planner.md`](../agents/planner.md) and one specialist
   (e.g. `agents/specialist-endurance.md`)
3. [`app/utils/prompt_loader.py`](../app/utils/prompt_loader.py) — how
   templates and configs get fused
4. [`app/graphs/sub_athlete_context/context_builder.py`](../app/graphs/sub_athlete_context/context_builder.py) — the
   single most important piece of domain logic; everything the planner
   sees flows through here
5. [`scripts/validate_plan.py`](../scripts/validate_plan.py) — the
   mechanical validator with its rule set

## Prompt-drift discipline

The HR-zone-briefing rule and a handful of cross-specialist directives
(warmup-drill de-duplication, RPE autoregulation table) appear in
multiple prompt YAMLs and agent definitions. This is duplication on
purpose — each specialist gets a self-contained brief — but it creates
drift risk when one rule evolves.

`scripts/audit_consistency.py` (function `check_override_drift`) scans
for the most common drift pattern: divergence between the framework
default and a wrapper override of `training_paradigms.md` or
`exercise_progressions.md`. New drift checks should follow that pattern
— add `check_<name>(...)` to `RULES`, register a category, and the
`config-auditor` will pick it up dynamically.

For prompt-level drift (e.g. the HR-zone block in three specialist
YAMLs), there is currently no automated check. The recommended workflow
is: edit the central rule in `config.example/training_paradigms.md`,
then re-render the prompts manually and run `/audit` to surface
inconsistencies before pushing.
