# Trainingsregeln — Planner

## Polarisiertes Training (Aufbauphase)
- 80 % der Einheiten in Z1–Z2 (easy)
- 20 % in Z4–Z5 (intensiv)
- Z3 wird aktiv gemieden
- Nach 2–3 aufeinanderfolgenden Easy-Einheiten kann eine intensive folgen, sofern HRV ≥ Baseline und TSB > −5
- HRV ≥ Baseline und TSB > 0 = grünes Licht für Intensität

## Pyramidales Training (8–10 Wochen vor Wettkampf)
- 70–80 % in Z1–Z2 (easy)
- 15–20 % in Z3–Z4 (moderat/Schwelle)
- 5–10 % in Z5 (hochintensiv)
- Z3 und Z4 werden gezielt trainiert (nicht gemieden), oft als Tempoläufe oder Schwellen-Intervalle
- Nach 2–3 Easy-Einheiten kann Schwellen- oder hochintensive Einheit folgen, sofern HRV ≥ Baseline und TSB > −5
- HRV ≥ Baseline und TSB > 0 = grünes Licht für spezifische Intensität (z. B. 10 km, Halbmarathon)

## Intensitätssteuerung
- TSB < −20: Sofortige Reduktion auf Z1 oder Ruhetag (zwingend, auch wenn Plan anderes vorsieht)
- TSB > 0 + HRV ≥ Baseline: Grünes Licht für Intensität

## HRV-Readiness (hrvReadiness — 7d-rollender ln-rMSSD vs 60d-Normalband)

`fetch_context.py` liefert das Top-Level-Feld `hrvReadiness`: der 7-Tage-rollende
Mittelwert des ln-rMSSD wird gegen ein 60-Tage-Normalband klassifiziert
(mean ± 0,5·SD der Tageswerte). Ersetzt den retired Last→HRV-Forecast — Last ist
kein Prädiktor mehr, nur paralleler CTL/TSB-Strom.

**Felder:**
- `verdict`: `clear` | `above` | `watch` | `hold` | `insufficient_data`
- `days_below`: aufeinanderfolgende Tage, an denen der 7d-Schnitt unter dem Band liegt
- `rolling_mean_ms`, `band_low_ms`, `band_high_ms`: 7d-Schnitt + Band (rücktransformiert)
- `cv`, `n_ref`: Variationskoeffizient + valide Tageswerte im 60d-Fenster

**Planungsregeln:**
- `clear` → 7d-Schnitt im Normalbereich, geplanten Reiz fortsetzen
- `above` → über dem Band, gute Erholung/Anpassung; leichter Aufbau möglich, wenn andere Signale passen
- `watch` → 1–2 Tage unter Band, weiches Signal: fortfahren, in `coaching_notes` vermerken, Confounder erfragen
- `hold` → 3+ Tage unter Band, hartes Signal: Erholung ist Default (an den combined HRV+RHR-Overload-Trigger angelehnt)
- `insufficient_data` → <30 valide Tageswerte im 60d-Fenster: Band nicht berechenbar, Rückfall auf die 90d-Median+5%-Logik; **weder** grünes Licht **noch** Warnsignal
- Muster über mehrere Tage beachten, Einzelwerte nicht überinterpretieren

**Advisory-Feld `hrvCvTrend`:** Tag-zu-Tag-CV-Trend (`rising`/`stable`/`falling`) als Früh-NFOR-Hinweis (Plews 2012) — nur informativ, **kein** harter Trigger.

**Top-Level-Feld `hrvReviewPending`:** gesetzt, wenn `hrvReadiness.verdict` `watch`/`hold` ist und noch keine `HRV-Review`-NOTE das Below-Band-Fenster abdeckt. Chef-Trainer fragt Athlet bei /wellness oder /training (1x pro Tag) nach externen Faktoren.

## Chronischer Schlafmangel (sleepTrend)
- `sleepTrend` enthält den 7-Tage-Schnitt der Schlafdauer + Score
- Wenn `sleepTrend` mit ⚠️ markiert ist (Schnitt < 6.5h über ≥5 Tage): Intensität einen Grad reduzieren
  - Geplante Z4/Z5-Einheit → auf Z2/Z3 oder Recovery verschieben
  - Volumenpläne um ~15 % kürzen
  - Kein Doppeltag bei chronisch < 6h

## RHR-Trend als Overreaching-Frühwarnzeichen (rhrTrend)
- `rhrTrend` vergleicht 3-Tages-Schnitt (letzten 3 Tage) vs. 3-Tages-Schnitt (vor 5–7 Tagen)
- Wenn `rhrTrend` mit ⚠️ markiert ist (+>3 bpm Anstieg): konservative Tagesplanung
  - Intensität sperren (kein Z4/Z5) auch wenn HRV normal erscheint
  - 1–2 Easy-Tage oder Ruhetag einplanen, bis RHR-Trend stabilisiert
  - `dataWarnings` enthält dann auch automatisch einen Eintrag

## Interferenz-Mindestabstand Kraft + Lauf (Doppeleinheiten)
**Quelle:** Coffey & Hawley (2017), Wilson et al. (2012 — MSSE)

Bei Doppeleinheiten mit WeightTraining + Lauf gelten folgende Mindestabstände:
- WeightTraining (allgemein) → Lauf: **≥3h Abstand**
- WeightTraining mit Bein-Fokus (Tags: `legs` (oder Legacy `beine`), `plyo`) → Lauf: **≥6h Abstand**

Grund: Bein-Kraft vor dem Lauf erhöht metabolische Interferenz und CNS-Ermüdung signifikant. Der Abstand ermöglicht partielle Glykogen-Resynthese und reduziert mechanische Ermüdung.

**Reihenfolge:** WeightTraining IMMER vor dem Lauf (gleicher Tag). Nie umgekehrt.

**Startzeiten (workout_parser.py setzt dies automatisch um):**
- Standard-Doppeltag: Kraft 06:00 → Lauf 09:30 (06:00 + Kraft-Dauer + 3h)
- Bein-intensiv/Plyo + Lauf: Kraft 06:00 → Lauf 12:30+ (06:00 + Kraft-Dauer + 6h)

## Plyo-Integration (Planungsregeln)
- Als 5–10 min Warm-up-Block VOR einem Z2-Lauf: ok (selber Tag, Plyo zuerst)
- Als eigenständige Einheit: 48h Abstand zu Intervallen
- Longrun (>60 min) gestern: nur leichtes Plyo als Warm-up
- Normaler Z2-Lauf gestern: kein Hindernis für Plyo
- Zielfrequenz: 2–3x/Woche, 10–20 min reicht vollständig

## Verfügbare Trainingstypen (intervals.icu)
| Typ | Felder |
|-----|--------|
| Lauf (outdoor/indoor) | type="Run" |
| Indoor Rad | type="Ride", indoor=true |
| Kraft/Core/Plyo/Balance | type="WeightTraining", workout_type="STRENGTH" |
| Recovery (Foam Roller, Dehnen, Mobility) | type="Workout", workout_type="RECOVERY" |
| Ruhetag | type="Workout", workout_type="RECOVERY", duration_min=0, name="Ruhetag" |

## Tags-System
| Tag | Bedeutung |
|-----|-----------|
| run | Jede Laufeinheit |
| ride | Jede Radeinheit |
| core | Core-Übungen enthalten |
| legs | Bein-Kraft, Squats, Lunges, RDL etc. (Legacy-Alias: `beine` — wird beim Lesen weiterhin akzeptiert, neue Pläne emittieren `legs`) |
| plyo | Sprünge, Box Jumps, explosiv |
| balance | Balance Board, Einbeinstand, Slackline |
| mobility | Foam Roller, Dehnen, Mobility, Recovery |
| intervals | Intervalle, Schwellen-Einheiten, Z4/Z5-Blöcke |
| ninja | Ninja-Athletik-Einheit (Grip, Upper Body, Ninja-Core, Ninja-Plyo) |
| grip | Grip/Unterarm-Training (immer mit #ninja) |
| upperbody | Upper Body Pull/Push (immer mit #ninja) — aktive Bewegungssperren laut `athlete_static.md` Risikozonen beachten |

- `#plyo` = eigenständige Plyo-Einheit >15 min (setzt implizit auch `#legs`)
- `#legs` = Kraft-Fokus Beine ohne Sprungcharakter (Squats, Lunges, RDL). Legacy-Alias `#beine` wird weiterhin akzeptiert.
- Plyo als kurzes Warm-up (<10 min) wird nicht getaggt
- `#ninja` = eigenständige Ninja-Session ≥15 min, triggert Ninja-Spezialisten
- `#ninja #grip` = Schwerpunkt Griffkraft (Gripmaster, Farmer's Walk, Towel Grip)
- `#ninja #upperbody` = Pull (Rows, TRX Rows, Face Pulls) + Push (Push-ups, Dips); aktive Bewegungssperren (z.B. Schulter, Ellbogen) ergeben sich aus `athlete_static.md` Risikozonen
- `#ninja #core` = Ninja-spezifisches Core (Hollow Hold, L-Sit, Anti-Rotation)
- `#ninja #plyo` = Obstacle-spezifische Explosivität (Clap Push-ups, Lache-Drills)

**Abgrenzung Ninja vs. Complementary:**
| Tag-Kombination | Spezialist | Fokus |
|----------------|------------|-------|
| `#core` (ohne ninja) | Complementary | Running-Core (Dead Bug, Plank, Bird Dog) |
| `#ninja #core` | Ninja | Ninja-Core (Hollow Hold, L-Sit, Anti-Rotation) |
| `#plyo` (ohne ninja) | Complementary | Running-Plyo (Box Jumps, Bounds) |
| `#ninja #plyo` | Ninja | Obstacle-Plyo (Clap Push-ups, Lache-Drills) |

## Komplementäreinheiten – Fälligkeitsregeln
| Kategorie | Warn (🟡) | Überfällig (🔴) |
|-----------|-----------|-----------------|
| Core      | 4d        | 6d              |
| Beine     | 5d        | 7d              |
| Plyo      | 3d        | 5d              |
| Balance   | 5d        | 8d              |
| Mobility  | 3d        | 5d              |
| Ninja     | 2d        | 3d              |

- Beine/Plyo gesperrt (⛔) wenn Intervalle in letzten 2d
- Bei Longrun gestern: nur leichtes Plyo als Warm-up (5–10 min ok)
- Ninja Grip nicht gesperrt durch Intervalle (keine geteilte Muskelgruppe)
- Ninja Upper Body gesperrt wenn Intervalle in letzten 1d (CNS-Recovery)
- Ninja allgemein NICHT gesperrt durch Beine/Plyo (andere Muskelgruppen)
- Ninja Upper Body gesperrt (⛔) wenn raceInDays ≤ 2 (CNS + obere Körperspannung)
- Ninja Grip: raceInDays ≤ 1 gesperrt; raceInDays = 2 ok wenn leicht (Forearm Curl, kein Farmer's Walk)

## Ninja-Integration (Planungsfrequenz)
- 2–3x/Woche, 20–30 min standalone
- Minimale Interferenz mit Laufen (andere Muskelgruppen/Energiesysteme)
- ≥6h Abstand zu harten Intervallen empfohlen
- Kann an Easy-/Recovery-Tagen problemlos trainiert werden
