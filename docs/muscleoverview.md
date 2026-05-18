# Muscle Overview System — Dokumentation

> **Status:** Phase A — Datenbefüllung, keine Planer-Integration

---

## 1. Überblick

Das Muskel-Last-Tracking-System erfasst die Ermüdung sport-relevanter Muskeln über Trainingseinheiten hinweg. Ziel: Erkennen welche Muskeln überlastet oder untertrainiert sind, und wann sie wieder trainierbar sind.

**Sport-Abdeckung:** Laufen (L), Radfahren (R), Bouldern (B), Ninja (N)
**Muskeln:** ~72 in 17 Körperteilgruppen (Quelle: `config/muscle_db.md`)
**Zeitfenster:** Rollierend 30 Tage

---

## 2. Datei-Layout

```
coach/
├── config/
│   ├── muscle_db.md                   # 72 Muskeln + Regen-Tabelle (auto-injiziert als {muscle_db})
│   └── exercise_muscle_mapping.json   # ~45 Übungen initial (Kraft + Endurance-virtuelle)
├── data/
│   └── muscles/
│       ├── YYYY-MM-DD.json            # Session-Log pro Tag
│       ├── _e1rm_state.json           # EMA-geglätteter e1RM-State (α=0.3)
│       └── _unmapped.jsonl            # Queue ungekannter Übungen
├── app/
│   └── analytics/
│       ├── muscle_load.py             # Pure Funktionen: e1RM, RPE, Fatigue, Decay
│       └── exercise_parser.py         # Regex-Parser für Trainings-Descriptions
├── scripts/
│   ├── log_muscle_load.py             # Write: pro Activity oder --backfill N
│   └── muscle_overview.py             # Read: Terminal-Tabelle + Backfill + Unmapped-Review
├── docs/
│   └── muscleoverview.md              # Diese Datei
└── .claude/
    └── commands/
        └── muscleoverview.md          # /muscleoverview-Kommando
```

---

## 3. Kern-Formeln (sport­wissenschaftlich validiert)

### 3.1 e1RM

- **Brzycki** (Reps 2–10): `e1RM = w × 36 / (37 − reps)`
- **Epley** (Reps >10): `e1RM = w × (1 + reps/30)`
- Switching-Point bei reps=10
- EMA α=0.3 für Session-übergreifende Glättung

*Quellen: Brzycki 1993, Epley 1985*

### 3.2 RPE → RIR (Zourdos-Konvention)

```python
def rpe_to_rir(rpe):
    if rpe >= 6.0:
        return max(0.0, 10.0 - rpe)   # RPE 8 → 2 RIR
    return 5.0 + (6.0 - rpe)           # RPE 4 → 7 RIR (warm-up Plateau)
```

*Quelle: Zourdos et al. 2016 (OMNI-RES)*

### 3.3 Fatigue pro Set

```
set_load = reps × intensity × muscle_contribution
  intensity     = weight_kg / exercise_e1rm  (Fallback: RPE→Intensity-Tabelle)
  muscle_contribution = 1.0 primary | 0.5 secondary | 0.15 stabilizer
  
rpe_mult   = 1.0 wenn rpe ≤ 6, sonst 1.0 + 0.15 × (rpe − 6)
eccentric_mult = 1.4 wenn eccentric_dominant: true

set_fatigue = set_load × rpe_mult × eccentric_mult
```

*Quellen: Schoenfeld 2016 (Volume-Load), Paulsen et al. 2012 (Eccentric multiplier), Bompa 6th ed.*

### 3.4 Exponentieller Decay (Regeneration)

```
τ = regen_hours / ln(4)
fatigue_pct(h) = 100 × exp(−h / τ)
```

Bei `h = regen_hours`: ~25% Rest-Fatigue (Superkompensation beginnt).
Bei `h = 3 × regen_hours`: ~1.5% Rest (vollständig erholt).

*Quellen: Bompa & Haff 2009 (Periodization), Issurin 2010 (Residual training effects)*

### 3.5 Regenerations-Tabelle

| Gruppe | RPE <6 (low) | RPE 6–7 (mid) | RPE ≥8 (high) | Charakteristik |
|--------|-------------|---------------|----------------|----------------|
| small_dynamic | 24h | 48h | 72h | Unterarm-Flex/Ext, Wade |
| small_tendon | 36h | 60h | 96h | Grip-Holds, Finger-Ext Band |
| medium | 36h | 60h | 84h | Bizeps, Trizeps, Schulter |
| large | 48h | 72h | 96h | Quads, Glutes, Lats, Brust |
| core_deep | 24h | 36h | 60h | Core Anti-Rotation, tief |
| plyo_cns | 48h | 72h | 120h | ZNS + Sehnen bei Plyometrie |

### 3.6 Endurance-Fatigue

Zone-basierte Berechnung, getrennt von Strength-Fatigue (unterschiedliche Einheiten):

```
cardio_load[muscle] += zone_minutes × effort_factor_per_min × muscle_intensity
```

Effort-Faktoren: Z1/Z2 = 0.015/min | Z3 = 0.04/min | Z4/Z5 = 0.10–0.12/min

Downhill-Modifier (Run): eccentric_dominant × elevation_loss / 100m

*Prinzip: Cardio-Fatigue und Strength-Fatigue NICHT addieren — separate Skalen*

---

## 4. Exercise-to-Muscle-Mapping

Datei: `config/exercise_muscle_mapping.json`

Schema pro Übung:
```json
{
  "wrist_curl": {
    "aliases": ["wrist curl", "wrist curls"],
    "primary":    [{"muscle": "flexor_carpi_radialis", "intensity": 1.0}, ...],
    "secondary":  [{"muscle": "pronator_teres", "intensity": 0.4}],
    "stabilizer": [],
    "load_mode": "free_weight",
    "eccentric_dominant": false,
    "lever_factor": 1.0,
    "variant_factor": 1.0,
    "base_exercise": null
  }
}
```

`load_mode`-Optionen: `free_weight | bodyweight | isometric | band | grip_device | endurance`

Endurance-Einträge haben zusätzlich `_type: "endurance"`, `modality`, `zone_range`, `effort_factor_per_min`.

**Neue Übung hinzufügen:**
1. Muskeln recherchieren (EMG-Literatur oder Anatomie)
2. Eintrag in `exercise_muscle_mapping.json` anlegen
3. Alias in `app/analytics/exercise_parser.py` ergänzen (falls nötig)
4. `python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/log_muscle_load.py --backfill 30 --silent`

---

## 5. Datenfluss

```
intervals.icu Activity
    ↓ (description text)
exercise_parser.py → ParsedExercise[]
    ↓ (match_to_mapping_key)
exercise_muscle_mapping.json
    ↓ (compute_set_fatigue)
muscle_load.py → SessionMuscleLoad per Muskel
    ↓ (write)
data/muscles/YYYY-MM-DD.json
    ↓ (aggregate + decay)
muscle_overview.py → Terminal-Tabelle
```

Für Endurance-Activities:
```
intervals.icu Activity
    ↓ (icu_hr_zone_times)
aggregate_endurance_load(zone_minutes, modality, elevation_loss)
    ↓
data/muscles/YYYY-MM-DD.json (cardio_load Feld)
```

---

## 6. Phase A → Phase B Migrations-Pfad

**Phase A (jetzt):** Write-Heavy, Read-Light. DB sammelt Daten. Nur `/muscleoverview` liest sie.

**Phase B (nach ~4–6 Wochen Validierung):**
1. `MUSCLE_OVERLAP_RULES` in `app/analytics/recovery.py` → deprecated
2. `context_builder._compute_planning_constraints` → neuer Block basierend auf Fatigue-Thresholds
3. Spezialisten-Prompts → Pflicht-Check (analog Ninja-Säulen-Rotation)
4. `planningConstraints.muscleRecovery` → verbindlich für Planner und Spezialisten

Entscheidung für Phase B: explizit nach Athlet-Review der Datenlage nach 4–6 Wochen.

---

## 7. Bekannte Limitierungen (V1)

- **Bodyweight-Leverage** ist fest (push-up 0.65, pull-up 1.0) — kein individueller Kalibrierungsmechanismus
- **Bandübungen**: e1RM nicht möglich → RPE-Proxy-Tabelle (RPE 6→0.70, 9→0.92)
- **Isometrische Übungen**: TUT × RPE-Tier-Tabelle → separate Skala, kein e1RM
- **Section-Header** in Descriptions (WARM-UP, BLOCK 1...) landen in `_unmapped.jsonl` als Rauschen — Review via `--review-unmapped`
- **Cardio vs. Strength Skalen** sind inkompatibel — nie addieren
- **Eccentric-Multiplier 1.4**: Spanne 1.3–1.6 in der Literatur; nach Validierungsphase nachjustieren

---

## 8. Literatur

- Bompa & Haff (2009): *Periodization: Theory and Methodology of Training* (6th ed.)
- Brzycki (1993): Strength testing — predicting a one-rep max from reps-to-fatigue. *JOPERD 64(1)*
- Epley (1985): Poundage Chart. *Boyd Epley Workout*
- Issurin (2010): New horizons for the methodology and physiology of training periodization. *Sports Med 40(3)*
- Kreher & Schwartz (2012): Overtraining Syndrome. *Sports Health 4(2)*
- Paulsen et al. (2012): Leucocytes, cytokines and satellite cells: what role do they play in muscle damage and regeneration following eccentric exercise? *Exerc Immunol Rev*
- Schoenfeld (2016): The mechanisms of muscle hypertrophy and their application to resistance training. *JSCR 24(10)*
- Zourdos et al. (2016): Novel resistance training-specific RPE scale measuring repetitions in reserve. *JSCR 30(1)*
