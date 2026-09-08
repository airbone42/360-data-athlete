# Athlete profile — Alex Demo

> Demo athlete used by the public framework when no private `config/` is mounted.
> Replace this file in your own `config/athlete_static.md` with real values.
> Anything athlete-specific (injuries, weights, PRs, equipment) belongs here.

## Identity
- Name (internal): Alex Demo
- Age: 35
- Body weight: 70 kg
- Height: 178 cm
- Training experience: 8+ years recreational running, 3 years strength
- Time zone: Europe/Berlin

## Personal records (illustrative)
- 5K: 22:30 (2024)
- 10K: 47:00 (2024)
- Half marathon: 1:45 (2024)
- Marathon: 4:00 (2023)

## Training availability
- Weekly running volume: 4–5 h
- Total weekly training: up to 8 h (run + complementary + balance)

## Injuries and active restrictions
*(Update this block whenever symptoms change. The Coach reads it on every
session start and tailors recommendations accordingly.)*

- None currently active.

## Risk zones (template)
| Zone | Status | Restrictions | Last update |
|------|--------|--------------|-------------|
| Achilles | clear | — | — |
| Knee | clear | — | — |
| Shoulder | clear | — | — |

Status values: `clear` / `monitoring` / `active-restricted` / `paused`.

### Planning-time head for a zone (optional, recommended once a row grows)

A zone row starts as a line and ends, months later, as a chronicle: episode
after episode appended to the same cell. Nobody reads a cell that long as a
rule — they read it as narrative and leave with an impression. The quiet
failure that follows is a hypothesis the chronicle itself already refuted
being reached for again, because the refutation was written as a correction in
prose and never as the operative sentence that follows from it.

Put a short head in front of the chronicle and declare it with a marker, so the
consistency audit can see that the row has one:

```markdown
<!-- lever-head: Achilles -->

**Achilles**

| | |
|---|---|
| **Levers that work** | … the variables that actually change the outcome |
| **NOT a lever — refuted** | … stated as a negative claim, with the evidence and date that refuted it |
| **Weak signal, do not steer by it** | … observations too thin to carry a decision, and why |
| **Red flags → practitioner** | … the escalation criteria |
```

The marker's key is matched against the table row's first cell, ignoring
emphasis, case and spacing. A row that declares a head is never flagged, however
long its chronicle grows — the chronicle is not the problem, its position is.

*Enforcement: `audit_consistency.py::check_chronicle_cell_bloat` (audit check
`CHRONICLE_HEAD`, offline) — MEDIUM once a single cell passes
`CHRONICLE_CELL_MAX_CHARS`. Tests: `tests/test_chronicle_cell_head.py`.*

## HRV measurement
- Primary device: wrist-based HRV (e.g. Garmin, Whoop, Amazfit)
- Manual validation device: optional (e.g. Polar H10 + Elite HRV)
