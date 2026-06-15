# Übungs-Progressionen (Framework-Defaults)

> **Framework-Defaults.** Diese Datei enthält Übungsdefinitionen,
> Progressionsvektoren (Last/Reps/Dauer-Logik) und generische
> Form-Hinweise — aber **keine athleten-spezifischen Last-/RPE-
> Tracking-Einträge** und **keine athleten-spezifischen Restrictions,
> Phase-Marker oder Equipment-Status**. Konkrete Einstiegsgewichte,
> aktueller Stand und individuelle Caveats werden pro Athlet in
> `config/exercise_progressions.md` gepflegt (überschreibt diese
> Datei via Loader-Fallback). Spezialisten lesen den vollständigen
> Stand aus der athletenspezifischen Version, sobald diese vorhanden
> ist.

Dieses File definiert für jede Übung den **Progressionsvektor**
(welche Variable wird zuerst gesteigert — Last, Reps, Hold-Time,
TUT, Dauer), Standard-Set-/Rep-Schemata, generische Form-Cues und
biomechanische Varianten-Faktoren. Konkrete Athleten-Werte gehören
in den Wrapper.

**Regel:** Spezialisten überschreiben keinen Wrapper-Eintrag ohne
explizites Athleten-Feedback. Updates nach jeder Einheit mit neuer
Übung oder RPE-Feedback erfolgen in der **Wrapper-Version**
(`config/exercise_progressions.md`), nicht in den Framework-Defaults.

---

## Varianten-Regeln (ZWINGEND bei allen Übungspaaren)

Wenn eine Übung eine biomechanisch schwächere Variante einer Basisübung ist, gelten diese Regeln — **ohne Ausnahme**:

- **Gewicht:** ≤ Gewicht der Basisübung × Variante-Faktor
- **Sätze:** Nicht höher als die Basisübung — außer bei explizit dokumentiertem Athleten-Feedback ("leicht", "RPE ≤5")
- **Reps:** Eher weniger als die Basisübung (schwächere Muskelmechanik = frühere Ermüdung)
- **Entscheidungshilfe:** Variante-Faktor steht pro Übung unten. Für nicht gelistete Paare: konservativ wählen (Faktor 0.7 wenn unsicher).

---

## Re-Eval-Feld (WHY-Persistenz für die Re-Evaluations-Kadenz)

Damit die Übungsauswahl nicht „blind" Session für Session übernommen,
sondern an natürlichen Grenzen (Erholungswoche, Phasenwechsel, Staleness)
gegen die aktuellen Ziele **gechallengt** wird, kann jede aktive Übung im
**Wrapper** (`config/exercise_progressions.md`) eine maschinenlesbare
Re-Eval-Zeile tragen:

```
- **Re-Eval:** dient=<Ziel/Phase> | eingeführt=YYYY-MM-DD | letzte-Re-Eval=YYYY-MM-DD | Status=keep
```

- `dient=` — welchem Ziel / welcher Phase (`competition_plan.md`) die Übung dient.
- `eingeführt=` — wann die Übung in die Rotation kam.
- `letzte-Re-Eval=` — wann zuletzt bewusst hinterfragt. **Steuert Trigger C**
  (`context_builder._parse_stale_exercises`): liegt das Datum weiter zurück
  als `athlete_status.md → staleness_weeks`, flaggt der Coach die Übung
  in `planningConstraints`, und der `/training`-Flow startet den
  `exercise-reviewer`-Agenten.
- `Status=` ∈ `keep | progress | swap | retire | pending`. `retire` nimmt
  die Übung aus der Staleness-Prüfung (nicht mehr in Rotation).

Die konkreten Re-Eval-Zeilen sind **athleten-spezifisch** und gehören in
den Wrapper, nicht in diese Framework-Defaults. Phasen-Plan und
`staleness_weeks` werden in `athlete_status.md` gepflegt (siehe dort die
Re-Eval-Trigger-Sektion). Nach einer bestätigten Re-Evaluation `Status=`
und `letzte-Re-Eval=<heute>` zurückschreiben (Staleness-Reset).

---

## Grip

### KB Horn Pinch
- **Progressionsvektor:** Hold-Time primär, Last sekundär
- **Standard-Schema:** 3×20–30s je Seite, RPE-Ziel 7–8
- **Progression:** Hold-Zeit auf 25–30s steigern wenn RPE ≤5; danach Last erhöhen (typische Stufe +1–2 kg)
- **Form:** Daumen aktiv gegen Finger, KB-Horn zwischen Daumen und Zeigefinger-Basis, Unterarm neutral

### Gripmaster Fingers (bilateral)
- **Progressionsvektor:** TUT / Reps primär
- **Progression:** TUT erhöhen oder Single-Finger-Isolationen einbauen

### Pinch Grip Plates (Hantelscheiben)
- **Progressionsvektor:** Hold-Time primär, Last sekundär
- **Standard-Schema:** 3×15–25s je Hand, RPE 7
- **Progression:** Wenn 3×20s @ aktuellem Gewicht @ RPE ≤6 → +0.5–1.25 kg pro Hand (Scheiben-Gestackt)
- **Form:** Glatte Seiten der Scheiben aneinander, Daumen einseitig, 4 Finger gegenüber. Scheibe seitlich am Bein hängen lassen, Arm gestreckt, Schulter passiv hängend, Skapula leicht depressed.
- **Ordnung im Workout:** Pinch IMMER nach Crush-Vorbelastung (Suitcase Hold + Hang) → niedrigere Einstiegslast nötig als isolierter Pinch-Tag.

### Farmer's Hold (KB, einarmig)
- **Progressionsvektor (Kraftausdauer-Tag):** Gewicht primär, Hold-Zeit sekundär. Begründung: Maximalkraft-Adaptation (Pinch-Force, Carry-Stabilität) wird primär über Last erreicht; Hold > 60s wandert in den Kraftausdauer-Bereich.
- **Standard-Schema (Kraftausdauer-Tag):** Hold-Zeit auf 30–45s halten, Gewicht-Steigerung wenn 3×30s @ aktuellem Gewicht @ RPE ≤6 → +2.5 kg.
- **Maximalkraft-Block (1×/Woche):** 3×3 Sätze @ 90% Tagesmax, Hold 8–15s, Pause 90–120s zwischen Sätzen. Gewicht steigern wenn 3×3 @ 12s @ RPE ≤7 sauber.
- **Form-Cue:** Asymmetrische Last belastet QL/Erector spinae/Multifidus — bei hohen Lasten ist Rücken-Aktivierung im Warm-up (Cat-Cow, Bird Dog, Side Plank) ratsam, sonst Risiko kalter Aktivierung.

### Wrist Curls
- **Progressionsvektor:** Gewicht primär, Reps reduzieren. RPE 4 zeigt zu leicht für Adaptation. Reps-Erhöhung > 15 wandert in Lokal-Endurance, kein Kraftgewinn.
- **Standard-Schema:** 3×8–12 je Seite, RPE-Ziel 7–8. Wenn 3×10 @ aktuellem Gewicht @ RPE ≤6 erreicht → +1 kg.
- **Maximalkraft-Variante (1×/Woche im Pull/Grip-Block):** 4×5–6 je Seite, RPE 8. Pause 90s zwischen Sätzen.
- **Hinweis:** Flexion + Extension gleichzeitig (Agonisten-Balance für Sehnenprävention) — Reverse Wrist Curls mit Faktor 0.7 fortführen.

### Reverse Wrist Curls
- **Variante-Faktor:** 0.7 vs. Wrist Curls (Extensoren biomechanisch schwächer als Flexoren in dieser Bewegungsbahn)
- **Progression:** analog Wrist Curls, aber immer 1–2 Reps weniger als Wrist Curls auf gleichem Gewicht

### Finger-Extensoren Band
- **Progressionsvektor:** Bandstärke primär, Reps sekundär
- **Progression:** stärkeres Band wenn RPE ≤5 über 2 Einheiten, oder auf 20 Wdh steigern
- **Sportphysiologischer Fokus:** strukturelle Gegenbewegung zu Flexoren — IMMER nach Grip-Block

---

## Pull / Physio

### Latzug (Physio-Protokoll)
- **Progressionsvektor:** Last sekundär, Form-Qualität primär (Scapula-Retraktion)
- **Fokus:** Scapula-Retraktion (nicht Trapezius) — Schulterblätter nach unten-hinten, DANN Ellbogen

### Row (Zugseil/KH, Physio-Protokoll)
- **Progressionsvektor:** Last sekundär, Form-Qualität primär
- **Fokus:** Schulterblatt am Ende aktiv nach hinten-unten, Ellenbogen am Körper

### TRX Row
- **Progressionsvektor:** Winkel primär (Steilheit erhöhen), Last sekundär (Weste)
- **Hinweis:** Bei dokumentierten Seiten-Asymmetrien (Schon-/Überkompensation) bewusst ausgleichen, Kontrolle dominiert Volumen

### Supinated Row (Tisch-Hang)
- **Progressionsvektor:** Winkel primär, Reps sekundär
- **Hinweis:** Bei Seiten-Überkompensation Schwächeren-Seite führen lassen

---

## Core

### Hollow Rock
- **Progressionsvektor:** Reps primär, Lever-Länge sekundär
- **Progression:** +2 Wdh wenn RPE ≤5; Arme überkopf wenn RPE ≤4 über 2 Einheiten

### L-Sit Tuck Hold (Stühle, mit Handschuhen)
- **Progressionsvektor:** Hold-Time primär, Lever-Variante sekundär
- **Hinweis:** Volle L-Sit-Variante (Beine gestreckt) ist nur sinnvoll bei ausreichender Hamstring-Mobilität — sonst verlagern verkürzte Hamstrings Last in Hüftbeuger, Core-Reiz geht verloren. Tuck Hold ist die robuste Eingangsvariante.
- **Vorbereitung im Warm-up:** Wrist-Mobility 30s je Richtung + Reverse Wrist Curls 3×12 mit leichter KH (Wrist-Aufbau parallel zur Hold-Progression)
- **Form:** Latissimus zuerst aktivieren (Schulterblätter „in Hosentaschen") DANN Hüfte

### Pallof Press Band (Sprossenleiter)
- **Progressionsvektor:** Anker-Distanz primär (Hebel), Reps sekundär
- **Progression:** wenn RPE ≤5 → Volumen 3×16 ODER weitere ~10 cm Anker-Distanz
- **Form:** Anti-Rotation, Band auf Brusthöhe, Hüfte streng frontal — kein Wegdrehen
- **per_side:** true

### Dead Bug Contralateral mit KB
- **Progressionsvektor:** Reps primär, KB-Last sekundär
- **Progression:** wenn RPE ≤6 → 3×12/Seite ODER Last erhöhen
- **per_side:** true
- **Hinweis:** LWS-Selbstreglung: bei Spalt am Tiefpunkt Bein nicht weiter senken; KB-Arm bewegt sich kontralateral mit (Richtung Boden hinter Kopf, synchron mit opposite Bein)
- **Reihenfolge-Warnung:** Tempo 3-1-2 macht die Übung sehr lang → Stir-the-Pot DANACH ist überdosiert (siehe Stir-Eintrag)

### Stir-the-Pot (Pezziball)
- **Progressionsvektor:** Lever-Länge primär (Füße weiter zurück), Tempo / Reps sekundär
- **Progressions-Optionen:**
 - Option A: Stir-the-Pot **VOR** Dead Bug platzieren — frische Core-Spannung
 - Option B: Tempo **2-0-2** + Reps **3×8** je Richtung (entspricht ~16s/Satz statt 36s)
 - Option C: 3×10 normal + nur Lever-Progression (Füße einen Schritt weiter zurück)
- **Form-Cue:** Hüfte unter dem Brustbein einrasten — kein Hohlkreuz, Kreis kommt aus den Schultern
- **per_side:** false (je Richtung statt je Seite)

### Y-Balance Reach (statisch, einbeinig)
- **Progressionsvektor:** Stabilitätswert (S-Rating) primär, dann Last / Augen-zu
- **Progression:** S2 ist Baseline. Bei S1 → +Last (KH in der Hand des freien Beins) ODER längerer Reach. Bei S3 → 2×3 mit Augen zu, dann zurück auf 3×3 normal.
- **Hinweis:** Standbein leicht gebeugt, freier Fuß tippt sanft, kein Aufstützen. Standbein-Hüfte aktiv gegenhalten.
- **per_side:** true

### Hollow Hold
- **Progressionsvektor:** Hold-Time primär
- **Hinweis:** Arme am Körper, Lendenwirbel permanent am Boden

### Plank
- **Progressionsvektor:** Hold-Time primär
- **Standard-Schema:** 3×30–45s, RPE-Ziel 7

### Side Plank
- **Progressionsvektor:** Hold-Time primär
- **Standard-Schema:** 3×20–30s je Seite, RPE-Ziel 7
- **per_side:** true

---

## Curl-Varianten

### Kurzhantel-Curl (supiniert) — Basisübung
- **Progressionsvektor:** Last primär
- **Standard-Schema:** 3×10–12 je Seite, RPE-Ziel 7–8
- **Muskel:** Biceps brachii primär, Brachialis sekundär

### Hammer Curl (neutral)
- **Variante-Faktor:** 0.9 vs. Kurzhantel-Curl (neutrale Griffposition — Brachioradialis + Brachialis stärker aktiv, Biceps etwas weniger)
- **Progression:** analog Kurzhantel-Curl

### Reverse Curl (proniert)
- **Variante-Faktor:** 0.6 vs. Kurzhantel-Curl (Brachioradialis-dominant, Handgelenk-Extensoren mitbelastet, biomechanisch schwächste Griffposition)
- **Pflicht:** Gewicht ≤ Hammer Curl ≤ Kurzhantel-Curl. Sätze NIEMALS höher als Kurzhantel-Curl ohne expliziten Grund.
- **Muskel:** Brachioradialis primär, Extensor carpi radialis, ECRL

---

## Maximalkraft-Übungen

Diese Sektion ist Heimat der Übungen für die zwei Maximalkraft-Blöcke (Bein + Pull/Grip). Format generell: **4×4–6 Reps @ 80–85% 1RM, RPE 7–8, 90–180s Pause zwischen Sätzen.** Tempo kontrolliert (3-1-X), keine Schwung-Reps.

### Pull/Grip-Block (1×/Woche)
Integriert in Ninja-Tag (10–15 min, vor oder nach Kraftausdauer-Block je nach Energieniveau — bei Maximalkraft-Fokus: Block ZUERST).

#### Weighted TRX Row
- **Variante-Faktor:** 1.2 vs. TRX Row Bodyweight (Steilheit + Weste)
- **Progressionsvektor:** Winkel primär (steiler = härter), Westen-Last sekundär
- **Standard-Schema:** 4×6, RPE-Ziel 8. Wenn 4×6 @ RPE ≤7 → +2.5 kg Weste oder Winkel reduzieren.
- **Hinweis:** Schulterblatt zuerst aktiv nach hinten-unten ziehen, Ellenbogen am Körper, kein Trapezius-Hochzug.
- **Stop-Kriterium:** Schulterschmerz, Knacken oder Schulter-Wärme → zurück auf BW-TRX Row, Physio-Konsultation.

#### Heavy Wrist Curls (Maximalkraft-Variante)
Siehe Wrist Curls oben — Maximalkraft-Variante: 4×5–6, RPE 8.

#### Heavy Farmer's Hold (Maximalkraft-Variante)
Siehe Farmer's Hold oben — Maximalkraft-Block: 3×3 Sätze @ 90% Tagesmax, Hold 8–15s.

#### KB Horn Pinch — Max-Pinch-Force-Variante (optional)
- **Hintergrund:** Standard-Eintrag (oben) ist Endurance-Pinch (Hold-Zeit). Für Maximal-Pinch-Force: kürzer + schwerer.
- **Progressionsvektor:** Last primär, Hold-Time fix kurz
- **Standard-Schema:** 3×8s je Seite, RPE-Ziel 8. Pause 60s. Wenn 3×8s @ aktuellem Gewicht @ RPE ≤6 → +1 kg.

### Bein-Block (1×/Woche)
Integriert in Bein-Tag (15–20 min). **Voraussetzung Start:** Falls eine aktive Bein- oder Sehnen-Restriktion im Wrapper-`athlete_static.md` gelistet ist, gelten die dort dokumentierten Freigabe-Kriterien (funktionale Tests, Schmerzfreiheit, Plyo-Toleranz). Bis dahin: Goblet Squat als Aufbau-Übung mit moderatem Gewicht (RPE 6–7), nicht Maximalkraft-Range.

#### Goblet Squat — Bein-Maximalkraft-Basisübung
- **Progressionsvektor:** Last primär
- **Tiefe:** Hüftcrease unter Knie ("below parallel"), Fersen am Boden, Brust auf
- **Maximalkraft-Format:** 4×4–6, ~85% angenommenem 1RM, RPE 7–8. Pause 120–180s. Steigerung +2.5 kg KB wenn 4×6 @ RPE ≤7 sauber.
- **Einstieg-Test (vor Maximalkraft-Start):** 3×8 mit ~50% angenommenem 1RM → RPE und Form dokumentieren. Wenn schmerzfrei und sauber → Einstieg.
- **Stop-Kriterium:** Achilles-Reizung morgens nach Session, Knie-Schmerz, Hüft-Asymmetrie → zurück auf 3×8 mit moderatem Gewicht.

#### Trap Bar Deadlift (alternativ zu Goblet Squat)
- **Progressionsvektor:** Last primär
- **Format:** 4×4–6 @ 80–85% 1RM, RPE 7–8.
- **Hinweis:** Hinge-Pattern (Hüfte zurück, Brust auf), kein „Squat-Style" Trap Bar. Bei Trap-Bar-Verfügbarkeit gegenüber Goblet Squat zu bevorzugen wegen kniefreundlicher Hebellängen und geringerer Lendenwirbel-Last.

#### Single-Leg RDL (Hamstring/Glute-Maximalkraft, einbeinig)
- **Variante-Faktor:** 0.5 vs. bilateraler RDL (einbeinig × asymmetrisch)
- **Progressionsvektor:** Last primär
- **Maximalkraft-Format:** 3×6 je Seite, KH in Hand des freien Beins (kontralateral), RPE 7–8. Steigerung wenn 3×6 @ RPE ≤7.
- **per_side:** true
- **Hinweis:** Standbein-Knie leicht weich, Hüfte zurück, Rücken neutral. Bei dokumentierter Hamstring-Tightness im Wrapper Stretch-Block im Warm-up empfohlen.
