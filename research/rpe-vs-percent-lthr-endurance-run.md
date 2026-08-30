# %LTHR ↔ RPE-Korridor für Laufblöcke (8–30 min) — Diskrepanz-Check gegen falsche Vorgabe-Bänder

**Erstellt:** 2026-08-30

## TL;DR

1. **Eine belastbare Punkt-Zuordnung „x % LTHR → RPE y" gibt die Literatur nicht her — nur einen Korridor mit erheblicher Streuung.** Die grösste Einzelstudie (Scherr 2013, N=2 560) findet an der individuellen anaeroben Schwelle **RPE 13,6 ± 1,8** (Borg 6–20; ≈ **CR10 4–5**), an der 4-mmol-Schwelle **RPE 14,1 ± 2,0** (≈ CR10 5). Die Korrelation RPE↔HF ist nur *moderat* (r = 0,74 bei Scherr; **r = 0,62** im Chen 2002-Meta über 64 Studien) — schwächer als RPE↔Laktat (r = 0,83 / 0,57) und deutlich schwächer als RPE↔Pace/Power bei Trainierten.
2. **Für 8–30-min-Blöcke bei einem trainierten Läufer** ergibt sich als operativer Erwartungs-Korridor (mid-CR10):

   | Block-Intensität | Erwartungs-CR10 (Median-Läufer) |
   |---|---|
   | **~85–89 % LTHR** (Z2/Aerobic) | 2–4 |
   | **~90–94 % LTHR** (Z3/Tempo) | 4–6 |
   | **~95–99 % LTHR** (Z4/Threshold, sub-LTHR) | 5–7 |
   | **~100–102 % LTHR** (Z5a/VO₂-Nähe) | 7–8 |
   | **≥ 103 % LTHR** (Z5b+) | 8–10 |

   Der Korridor ist **~2 CR10-Punkte breit** — er beschreibt das mittlere Drittel der Population, nicht einen physiologischen Zielwert.
3. **Die Streuung ist gross und teilweise irreduzibel:**
   * Interindividuell an der Schwelle: **SD ≈ 1,5–2 CR10-Punkte** (Scherr 2013), Range in Läufer-Kohorten bis **RPE 10,2–16,5** an derselben LT (PMC4429818).
   * Intraindividuell (Test-Retest, gleiche Belastung): **SEM 0,3–1,05 CR10-Punkte, CV 4–11 %** (Zanini 2025), ICCs 0,71–0,95 — deutlich schlechter als bei HF.
   * Konsequenz: **eine Diskrepanz ≤ 1 CR10-Punkt ist Rauschen, keine Diagnose.**
4. **Diagnostisch belastbare Auslöse-Schwelle des Checks (konservativ, aus der SD abgeleitet):**
   * **RPE ≥ 2 Punkte UNTER dem Korridor-**Boden** eines Blocks ≥ 8 min in ≥ 90 % LTHR** = **einzelnes Signal** (nicht Rauschen, aber noch nicht Beweis).
   * **RPE ≥ 3 Punkte unter dem Korridor-Boden** ODER **≥ 2 Punkte unter Boden über ≥ 2 Qualitätseinheiten in 14 d** = **Bandes-Kalibrierungs-Verdacht** (Meldung wert).
   * Die Schwelle sitzt bewusst *jenseits* der ~2-SD-Streuung, damit der Check nicht bei jeder Tagesform-Schwankung feuert. Ein Check, der bei normaler Varianz meldet, wird ignoriert und ist schlechter als keiner (Grundprinzip aus [rpe-gate-validity-isometric-holds.md](rpe-gate-validity-isometric-holds.md)).
5. **Bekannte Störgrößen, die den Check ausschliessen oder mindestens flankieren muss** (jede senkt RPE bei gegebener HF **ohne** dass das Band falsch wäre): Hitze/Umgebungswärme, Dehydration/Cardiac Drift in Blöcken > 20 min, Koffein (~5–6 % RPE-Reduktion, Doherty & Smith 2005), **Outdoor vs. Laufband (~2 CR10-Punkte Differenz zugunsten Outdoor**, Ceci 1991 / PMC11135770), sehr kurze Blöcke (< 8 min: RPE hat Rampen-Kinetik, hinkt der HF hinterher), Musik/Ablenkung, Chest-Strap-Rauschen im minute-0–10-Fenster (siehe [cardiac-startup-drift.md](cardiac-startup-drift.md)).
6. **Umgekehrte Richtung ist diagnostisch stärker, aber anders zu lesen.** RPE **über** dem Korridor bei sauberer HF ist ein Readiness-Signal (Ermüdung/Infekt/Hitze/Eisenmangel), **kein** Signal für ein falsch gesetztes Band. Schwelle konservativer setzen (**RPE ≥ 2 Punkte über Korridor-Obergrenze über ≥ 2 Einheiten**) und in den HRV-/RHR-Kontext routen, nicht in eine Band-Rekalibrierung.
7. **Ehrlichkeits-Auflage:** Der Check ist ein **Verdachts-Auslöser**, keine Beweisführung. Er ersetzt weder ein neues Schwellentest, noch macht er eine einzelne %-LTHR-Zahl belastbarer, als sie ist. Er soll den Bias „das war leichter als geplant → also ist der Athlet in Form" gegen die Konkurrenzhypothese „das war leichter als geplant → also war die Vorgabe zu tief" mechanisch neutralisieren (Paradigma-Anker: framework/CLAUDE.md → *„A rehearsal that comes back far easier than the band predicts is evidence against the band"*).

## Question / Trigger

Auslöser: coach-geflaggte Unsicherheit aus realer Anwendung. Ein Audit-
Check soll automatisch melden, wenn eine absolvierte Qualitätseinheit
deutlich leichter zurückkommt, als ihr HF-Anteil erwarten lässt — als
mechanische Gegenkraft gegen die im framework-Paradigma („No silent
conservatism", *rehearsal-below-expectation*-Klausel) beschriebene
Fehl-Lesart, ein leichtes Rehearsal als „Formzuwachs" statt als
„Band zu tief" zu interpretieren.

Konkret geht es um Laufeinheiten mit Belastungsblöcken von etwa 8–30 min
in ≥ ~85 % LTHR (Tempo/Threshold/VO₂-nah). Offen war:

1. Welchen RPE-Korridor lässt sich aus der Literatur für einen gegebenen
   %LTHR-Anteil überhaupt belastbar ableiten?
2. Wie gross ist die natürliche Streuung (inter- und intraindividuell),
   die die Auslöse-Schwelle des Checks nach unten begrenzt?
3. Welche Diskrepanz ist deshalb minimal nötig, damit die Meldung
   informativ und nicht rauschgetrieben ist?
4. Welche legitimen Störgrößen (Hitze, Drift, Koffein, Laufband, kurze
   Blöcke, Mess-Artefakte) müssen den Check flankieren oder ausschliessen,
   damit er nicht falsche Alarme produziert?
5. Ist die umgekehrte Richtung (RPE deutlich über Erwartung) dieselbe
   Diagnose oder eine andere?
6. Ist HF überhaupt der richtige Vergleichspartner für RPE — oder wäre
   Pace/Power der bessere Anker?

## Findings

### 1. Was die Literatur als %LTHR → RPE-Korridor tatsächlich hergibt

**Der Punktwert-Zuordnung fehlt die Evidenz — der Korridor ist das, was übrig bleibt.**

* **Scherr et al. 2013** (Eur J Appl Physiol; **N = 2 560**, Zykloergometer + Laufband, submaximal-inkremental) — die grösste Einzeluntersuchung zum Thema:
  * an der **Laktatschwelle (LT)**: RPE **10,8 ± 1,8** (Borg 6–20)
  * an der **individuellen anaeroben Schwelle (IAT)**: RPE **13,6 ± 1,8**
  * an fixer **3 mmol/L**: RPE **12,8 ± 2,1**
  * an fixer **4 mmol/L**: RPE **14,1 ± 2,0**
  * Korrelation RPE↔HF: **r = 0,74** (p < 0,001)
  * Korrelation RPE↔Laktat: **r = 0,83** (p < 0,001)
  * Kernaussage: „Gender, age, coronary artery disease, physical activity status and exercise testing modality did not influence this association significantly."
  * **Umrechnung Borg 6–20 → CR10:** Borg 6–20 ≈ (CR10 × 2) + 6. Damit: LT ≈ CR10 2–3, IAT ≈ CR10 4–5, 4 mmol ≈ CR10 5.

* **Chen et al. 2002** (J Sports Sci; **Meta-Analyse über ~64 Studien, ~2 000 Probanden**):
  * gewichtete Validitäts-Korrelation RPE↔HF: **r = 0,62**
  * RPE↔%VO₂max: **r = 0,64**
  * RPE↔VO₂: **r = 0,63**
  * RPE↔Laktat: **r = 0,57**
  * RPE↔Ventilation: **r = 0,61**
  * Kernaussage: Korrelationen sind **moderat**, nicht stark; „large inter-individual variability during graded treadmill tests" schränkt die Verwendung von RPE zur Präskription homogener Intensität ausdrücklich ein.

* **Studie an jungen Läuferinnen** (PMC4429818, Kang et al.):
  * CR10 an LT: **3,40 ± 0,83**
  * Borg 6–20 an LT: **12,3 ± 1,6**
  * **Range** in der Kohorte an derselben LT: **RPE 10,2 – 16,5** (also **~6 Punkte auf der 6–20-Skala** ≈ **~3 CR10-Punkte** allein durch Interindividualität).
  * „CR-10 ≈ 3 as non-invasive marker for estimating lactate threshold across different fitness levels in young females."

**Konvention LTHR ↔ LT2.** Friel definiert LTHR über den 30-min-TT-Anker
(HF-Mittel der letzten 20 min) — konzeptionell nahe an der IAT / MLSS /
4-mmol-Region. Die Scherr-IAT von RPE 13,6 ± 1,8 → **CR10 4–5**
entspricht damit „RPE am LTHR". Genau an LTHR (≈ 100 % LTHR) ist also
CR10 **~5** der Punkt-Schätzer, mit ±1,5–2 SD Streuung → Korridor **4–7**.

**Extrapolation auf %LTHR unter/über Schwelle** (10 % LTHR-Anstieg ≈ 1–2
Borg-6–20-Punkte oder ~1 CR10-Punkt, aus Scherr 2013 und den
klassischen Friel-Zonen-Tabellen abgeleitet, **nicht direkt aus einer
Studie berichtet — Extrapolation deshalb explizit als solche
gekennzeichnet**):

| Block-Intensität (~ Friel-Zone) | Erwartungs-CR10 Median | Korridor (± 1 SD Population) |
|---|---|---|
| ~85–89 % LTHR (Z2) | 3 | **2–4** |
| ~90–94 % LTHR (Z3) | 5 | **4–6** |
| ~95–99 % LTHR (Z4, sub-LTHR) | 6 | **5–7** |
| ~100–102 % LTHR (Z5a) | 7,5 | **7–8** |
| ~103–106 % LTHR (Z5b) | 9 | **8–10** |
| ≥ 106 % LTHR (Z5c) | 10 | **9–10** (Skala-Deckel) |

**Wichtiger Vorbehalt für 8–30-min-Blöcke:** RPE ist **zeitabhängig**.
Session-RPE (Foster 2001) ist gültig ab **~20–30 min** Bewegungsdauer;
kurze Blöcke (< 8–10 min) unterschätzen den späteren RPE systematisch
(die RPE-Rampe hat einen Slow-Component analog zur VO₂-Kinetik). Für
einen **8-min-Block** liegt das ehrliche Erwartungs-Zentrum eher am
**unteren Rand** des Korridors; für einen **30-min-Block bei
konstantem Watt/Pace** driftet der RPE bis zum Ende der Belastung
typisch um **1–2 CR10-Punkte nach oben**, während die HF durch
Cardiac Drift ebenfalls steigt — deshalb ist der Korridor über die
Block-Dauer *nach oben verschieblich*, nicht statisch.

### 2. Streuung — Ober- und Untergrenze der Auslöse-Schwelle

**Interindividuell** an der Schwelle:
* SD in Scherr 2013: **±1,8–2,0 Borg-6–20-Punkte** ≈ **±0,9–1,0 CR10**.
* Range in der jungen-Läuferinnen-Studie (PMC4429818): **10,2 – 16,5
  auf Borg 6–20** an derselben LT ≈ ~3 CR10-Punkte breit.
* Konservative Lesart: **2 SD = ~2 CR10-Punkte** um den Populations-Median
  umschliessen ~95 % der individuellen Zuordnungen an einem Fixpunkt.

**Intraindividuell (Tages-Streuung derselben Person):**
* Zanini 2025 (PMC12107507): 90-min-Läufe, RPE nach 30 min und 75 min zwischen zwei Wiederholungen **nicht signifikant reproduzierbar** (p = 0,06 / 0,08) — RPE ist damit **das *unzuverlässigste* Signal** im Vergleich zu HF, Ventilation und Ökonomie in derselben Studie.
* Reviews an submaximaler Intensität: ICC **0,71–0,95**, SEM **0,30–1,05 CR10-Punkte**, CV **3,98–11,04 %**.
* Konservative Lesart: **eine ±1-CR10-Punkt-Abweichung von einem Sitzungs-Erwartungswert derselben Person ist Test-Retest-Rauschen** und darf nicht Diagnose sein.

### 3. Diagnostische Diskrepanz-Schwelle des Checks

Aus (1) und (2) folgt der Auslöse-Rahmen. Die Schwelle liegt bewusst
jenseits von **2 SD** (Population) und **2 × SEM** (Test-Retest), damit
sie nur bei echten Signalen feuert:

**Primär-Auslöser (Verdacht, Meldung wert):**
* Block-Dauer ≥ 8 min UND
* Segment-HF ≥ 90 % LTHR (Cardiac-Startup-Fenster 0–10 min der Aktivität
  ausgeschlossen — siehe [cardiac-startup-drift.md](cardiac-startup-drift.md)) UND
* berichteter RPE (CR10, session- oder Segment-post) **≥ 2 Punkte unter der Korridor-Untergrenze** dieses %LTHR-Bandes.

**Verstärkung (starkes Signal, Band-Rekalibrierung angezeigt):**
* Diskrepanz **≥ 3 CR10-Punkte** in einer einzelnen Einheit, ODER
* Primär-Auslöser **≥ 2×** innerhalb der letzten **~14 d** oder **~3
  qualifizierender Quality-Sessions** — was zuerst eintritt.

**Warum genau ≥ 2 (nicht ≥ 1) als Primär-Schwelle:**
* SD interindividuell ≈ 1 CR10 → 1-Punkt-Abstand deckt sich mit
  natürlicher Populations-Varianz.
* SEM intraindividuell bis 1 CR10 → 1-Punkt-Abstand deckt sich mit
  Test-Retest-Rauschen derselben Person.
* Ein 1-Punkt-Alarm produziert deshalb **erwartungsgemäss** einen hohen
  Anteil False Positives und wird nach kurzer Zeit ignoriert (klassisches
  „Alarm-Fatigue"-Muster — Referenz-Analog: false-positive-Diskussion in
  [rpe-gate-validity-isometric-holds.md](rpe-gate-validity-isometric-holds.md)).
* Ein ≥ 2-Punkt-Alarm hat mindestens ~2× SD Abstand vom Korridor-Rand,
  ~4× SEM Abstand vom Sitzungs-Rauschen — belastbare Detektionsgrenze.

### 4. Störgrößen — was ausgeschlossen oder mindestens genannt werden muss

Jede der folgenden Störgrößen **senkt** den RPE bei gegebener HF (also in
Richtung des Primär-Auslösers), **ohne** dass das Vorgabe-Band falsch ist.
Der Check muss sie prüfen, bevor er als „Band zu tief" liest:

| Störgröße | Effekt | Muss der Check checken? |
|---|---|---|
| **Umgebungshitze** | HF hoch bei moderatem Empfinden — Périard 2015: „when exercise becomes protracted, a disassociation develops between relative exercise intensity, heart rate, and ratings of perceived exertion". Zusätzlich [heat-pace-penalty-at-fixed-hr.md](heat-pace-penalty-at-fixed-hr.md). | **Ja** — Wetter-Feld aus `context.weatherInfo` einbeziehen; Warm/Hot → Check pausieren oder Meldung als hitze-flankiert markieren. |
| **Cardiac Drift** in Blöcken > 20 min | HF steigt 5–10 % über die Belastung bei konstantem Watt/Pace/RPE. Ab 20 min ist der HF-Wert des Blocks systematisch überzogen relativ zum RPE. | **Ja** — Blocks > 20 min: entweder auf HF *des ersten Drittels* prüfen oder Drift-korrigieren; sonst falscher Primär-Auslöser bei jeder langen Threshold-Einheit. |
| **Koffein** | Doherty & Smith 2005 (Meta): RPE −5,6 % (95 % CI −4,5 bis −6,7 %) unter Koffein bei sonst gleicher Belastung — entspricht **~0,5–1 CR10-Punkt** an Threshold-Intensität. | **Nein** (mechanisch kaum verfügbar) — als generischer Confounder benennen, aber nicht mechanisch ausschliessen. |
| **Outdoor vs. Laufband** | Ceci 1991 / Neuere Reviews (PMC11135770): bei gleicher HF/Pace berichten Läufer **~2 CR10-Punkte niedriger outdoor** als indoor. | **Ja** — Laufband-Runs (`surface: treadmill`) sind der **erwartete** Fall des Erwartungs-Korridors; Outdoor-Runs sind systematisch **1–2 Punkte niedriger** — deshalb: Outdoor **−1 CR10 auf die Korridor-Untergrenze** vor Diskrepanz-Vergleich. |
| **Sehr kurze Blöcke (< 8 min)** | RPE-Rampe hat langsame Kinetik; der finale RPE eines kurzen Blocks liegt unter dem Steady-State-RPE derselben Intensität. | **Ja** — harte Untergrenze **≥ 8 min qualifizierende Block-Dauer**; Strides (< 30 s) und kurze VO₂-Reps (< 3 min) sind ausgeschlossen. |
| **Cardiac-Startup-Fenster 0–10 min** | Bekanntes Mess-/Kinetik-Artefakt (siehe [cardiac-startup-drift.md](cardiac-startup-drift.md)). Ein Block, der in den ersten 10 min der Aktivität liegt, hat unzuverlässige HF. | **Ja** — Block-Start ≥ 10 min nach Aktivitäts-Start ist Voraussetzung. |
| **Chest-Strap-Rauschen, GPS-Cadence-Lock** | Bekannter HF-Sensor-Fehler bei trockenem Startkontakt / Kadenz-Lock beim optischen Sensor. | **Ja** — data-warnings-Feld aus `fetch_context` prüfen; HR-Data-Quality < ok → Check aussetzen. |
| **Ablenkung / Musik / Rennen mit Gruppe** | Karageorghis-Literatur: RPE typischerweise ~0,5–1 CR10 unter Kontroll-Bedingung. | Als Kontext benennbar, nicht mechanisch prüfbar. |
| **Post-Meal / Glykogen-Status** | Marginal an Threshold-Intensität; bei nüchtern signifikant. | Nachrangig. |

**Konsequenz:** Ein Primär-Auslöser wird zum Verdacht erst nach dem
**Confounder-Sieb** — Reihenfolge: (a) Block-Dauer ≥ 8 min & Startzeit ≥
Minute 10 der Aktivität, (b) HR-Data-Quality ok, (c) Temperatur nicht
warm/heiss oder Meldung flankieren, (d) Surface (Outdoor: Korridor-
Untergrenze −1 anwenden), (e) danach RPE gegen adjustierten Korridor
vergleichen.

### 5. Umgekehrte Richtung — RPE deutlich ÜBER Erwartung

Diese Richtung ist **diagnostisch stärker etabliert** (kernkomponente des
Foster-2001-Session-RPE-basierten Overreaching-Monitorings), zeigt aber
etwas **anderes** als die niedrige Richtung an:

* **Kein** Band-Rekalibrierungs-Signal.
* Ein Readiness-/Recovery-Signal: die Einheit war für die aktuelle
  Verfassung des Athleten „zu hart", nicht das Band „zu hoch".
* Klassische Ursachen: kumulierte Ermüdung (ACWR-Spike), incipient
  Infekt, Schlafdefizit, Dehydration, Eisenmangel, Hitze mit gleichzeitig
  hoher HF — d. h. HF-RPE-Verhältnis ist erhalten, beide sind zu hoch
  für den Zielzustand.
* **Schwelle bewusst konservativer:** RPE ≥ 2 Punkte **über** der
  Korridor-Obergrenze in mindestens ~2 Einheiten innerhalb 14 d.
* **Routing:** in den bereits existierenden HRV-/RHR-/Combined-Overload-
  Pfad und in die Mental-Coach-/Physio-Trigger-Liste, **nicht** in eine
  Band-Rekalibrierung.

### 6. Ist HF überhaupt der richtige Vergleichspartner?

**Kurz: für die framework-Nutzung ja, mit einer starken Einschränkung.**

* Die Korrelation RPE↔HF (r = 0,62 Chen 2002 / 0,74 Scherr 2013) ist
  **schwächer** als RPE↔Pace/Power beim trainierten Läufer im
  Threshold-Bereich (etablierte Coach-Praxis; keine belastbare Meta-Zahl,
  aber konsistent in Trainingslehre-Literatur).
* Für **kurze Blöcke** ist Pace/Power der bessere RPE-Prädiktor (HF hat
  Kinetik-Lag); für **lange Blocks** driftet HF (Cardiac Drift), Pace/
  Power bleiben stabil → wieder Pace/Power der bessere Anker.
* HF ist trotzdem **die** operative Input-Grösse des Checks, weil (a)
  das framework-Ökosystem HF als Primär-Anker führt (%LTHR-Zonen aus
  `athlete_status.md`, HF-Zonen-Verteilung in `fetch_context`), (b)
  Pace-basierte Anker (GAP, NGP) auf Laufband und in Wechselwetter
  systemisch verrauscht sind, und (c) der Check nur **grobe** Diskrepanz
  gegen einen **breiten** Korridor prüft — dafür reicht HF-Auflösung.
* **Aber:** wenn eine Aktivität ein sauberes **Decoupling-Signal** (NGP:HR
  im Sinne von [compliance-decoupling-thresholds.md](compliance-decoupling-thresholds.md)) trägt und
  Decoupling ≤ 5 %, ist das ein **starkes Confirmatorisches Argument**,
  dass der Block-HF-Wert valide ist. Bei Decoupling > 10 % im selben
  Block ist der HF-Wert der zweiten Hälfte unzuverlässig und der Check
  hat auf die HF *der ersten Hälfte* zurückzugreifen.

## Primary sources

| Titel | Autoren | Jahr | Journal / Link | Kernaussage / Zitat |
|---|---|---|---|---|
| Associations between Borg's rating of perceived exertion and physiological measures of exercise intensity | Scherr J, Wolfarth B, Christle JW, Pressler A, Wagenpfeil S, Halle M | 2013 | Eur J Appl Physiol — [PubMed 22615009](https://pubmed.ncbi.nlm.nih.gov/22615009/) · [Springer](https://link.springer.com/article/10.1007/s00421-012-2421-x) | „Rating of perceived exertion was strongly correlated with heart rate (r = 0.74, p < 0.001) and blood lactate (r = 0.83, p < 0.001). The mean values for lactate threshold (LT) and individual anaerobic threshold corresponded to an RPE of 10.8 ± 1.8 and 13.6 ± 1.8, respectively. Fixed lactate thresholds of 3 and 4 mmol/L corresponded to RPEs of 12.8 ± 2.1 and 14.1 ± 2.0." N = 2 560. |
| Criterion-related validity of the Borg ratings of perceived exertion scale in healthy individuals: a meta-analysis | Chen MJ, Fan X, Moe ST | 2002 | J Sports Sci 20(11):873–899 — [PubMed 12430990](https://pubmed.ncbi.nlm.nih.gov/12430990/) | Weighted mean validity coefficients: RPE↔HR r = 0.62; RPE↔%VO₂max r = 0.64; RPE↔VO₂ r = 0.63; RPE↔lactate r = 0.57; RPE↔ventilation r = 0.61; RPE↔respiration rate r = 0.72. „Large inter-individual variability during graded treadmill tests" schränkt die Verwendung von RPE zur Präskription homogener Intensität ein. |
| Relationship between perceived exertion and blood lactate concentrations during incremental running test in young females (Kang et al.) | Kang J, Ratamess NA, Faigenbaum AD, Bush JA, u.a. | 2014 | J Exerc Sci Fit — [PMC4429818](https://pmc.ncbi.nlm.nih.gov/articles/PMC4429818/) | CR-10 an LT: „3.40 ± 0.83"; Borg 6-20 an LT: „12.3 ± 1.6"; Range „10.2 to 16.5". „CR-10 ≈ 3 as non-invasive marker for estimating lactate threshold across different fitness levels in young females." |
| Session-RPE Method for Training Load Monitoring: Validity, Ecological Usefulness, and Influencing Factors | Haddad M, Stylianides G, Djaoui L, Dellal A, Chamari K | 2017 | Front Neurosci 11:612 — [Frontiers](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2017.00612/full) · [PMC5673663](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5673663/) | Session-RPE (Foster 2001) über > 950 Studien angewandt, „validated by 36 studies". Konfundierende Faktoren u. a.: „environmental temperature, altitude, glycemia, the consumption of pharmacological and/or doping products, caffeine-, energy-, alcohol-, milk-chocolate-drinks". |
| A new approach to monitoring exercise training | Foster C, Florhaug JA, Franklin J, Gottschall L, Hrovatin LA, Parker S, Doleshal P, Dodge C | 2001 | J Strength Cond Res 15(1):109–115 — [ResearchGate](https://www.researchgate.net/publication/11645805_A_New_Approach_to_Monitoring_Exercise_Training) | Originalpublikation des Session-RPE-Verfahrens (single-item CR10 30 min post-session × Sitzungsdauer). Grundlage der Übertragbarkeit von during-exercise-RPE auf Session-RPE. |
| Adaptations and mechanisms of human heat acclimation | Périard JD, Racinais S, Sawka MN | 2015 | Scand J Med Sci Sports 25(S1):20–38 — [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/sms.12408) | „When exercise becomes protracted, a disassociation develops between relative exercise intensity, heart rate, and ratings of perceived exertion." — theoretischer Anker dafür, dass Hitze die HF-RPE-Kopplung systematisch löst. |
| Effects of caffeine ingestion on rating of perceived exertion during and after exercise: a meta-analysis | Doherty M, Smith PM | 2005 | Scand J Med Sci Sports 15(2):69–78 — [PubMed 15773860](https://pubmed.ncbi.nlm.nih.gov/15773860/) | „Caffeine reduced RPE during exercise by 5.6 % (95 % CI, −4.5 % to −6.7 %)." Regressionsanalyse: RPE-Reduktion erklärt ~29 % der Leistungsverbesserung. |
| Perceived exertion can be lower when exercising in field versus indoors (Ceci 1991 / neuere Bestätigungen) | mehrere; Zusammenfassung in Review 2024 | 2024 | [PMC11135770](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11135770/) | Bei gleicher HF/Pace **~2 CR10-Punkte niedriger outdoor** als indoor; bzw. bei gleichem RPE **66 % höhere Speeds outdoor** — starker Confounder. |
| Test–Retest Reliability of Running Economy and Other Physiological Parameters During 90 min of Running in Well-Trained Male Endurance Runners | Zanini et al. | 2025 | Scand J Med Sci Sports (SMS 70080) — [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/sms.70080?af=R) · [PMC12107507](https://pmc.ncbi.nlm.nih.gov/articles/PMC12107507/) | RPE bei 30 und 75 min zwischen Wiederholungen **nicht signifikant reproduzierbar** (p = 0,06 / 0,08); RPE das unzuverlässigste Signal im Vergleich zu HF, Ventilation, Ökonomie. |
| Joe Friel's Quick Guide to Setting Zones | Friel J | 2009+ | [TrainingPeaks](https://www.trainingpeaks.com/learn/articles/joe-friel-s-quick-guide-to-setting-zones/) | %LTHR-Zonen-Konvention: Z1 < 85 %; Z2 85–89 %; Z3 90–94 %; Z4 95–99 %; Z5a 100–102 %; Z5b 103–106 %; Z5c > 106 %. Coach-Standard, nicht Studien-Standard. |

## Application in framework

### Vorschlag für die Auslöse-Logik (direkt code-fähig)

Zwei Checks — einer für die **niedrige Richtung** (Band-Rekalibrierungs-Verdacht), einer für die **hohe Richtung** (Readiness-Verdacht). Beide arbeiten pro qualifizierendem Lauf-Block, nicht pro Aktivität.

```python
# Pseudo-Konfiguration (default; per Athlet in config/athlete_status.md
# überschreibbar analog impact_streak_max, zone_validation_protocol, etc.)
RPE_CHECK_DEFAULTS = {
    # Erwartungs-Korridor CR10 pro %LTHR-Band, [floor, ceiling]
    # abgeleitet aus Scherr 2013 IAT (CR10 5 ± 1 SD) + Extrapolation
    # 1 CR10-Punkt pro ~10 % LTHR
    "corridor": {
        "z2_low":  (85, 89,  2, 4),   # 85-89% LTHR -> CR10 2..4
        "z3":      (90, 94,  4, 6),
        "z4":      (95, 99,  5, 7),
        "z5a":    (100, 102, 7, 8),
        "z5b":    (103, 106, 8, 10),
        "z5c":    (107, 999, 9, 10),
    },
    # Minimal-Blockdauer, damit der RPE-Steady-State etabliert ist
    "min_block_min": 8,
    # Aktivitäts-Startpuffer (Cardiac-Startup-Fenster ausschliessen)
    "activity_start_buffer_min": 10,
    # Primär-Auslöser Niedrig: RPE >= 2 CR10 unter Korridor-Floor
    "low_discrepancy_primary": 2,
    # Verstärkung Niedrig: >= 3 CR10 in einer Einheit ODER
    #                     >= 2 CR10 in >=2 Einheiten in 14 d
    "low_discrepancy_strong_single": 3,
    "low_discrepancy_strong_recurrent_count": 2,
    "low_discrepancy_strong_recurrent_window_days": 14,
    # Hohe Richtung: symmetrisch, aber default nur "recurrent" meldet
    "high_discrepancy_primary": 2,
    "high_discrepancy_recurrent_count": 2,
    "high_discrepancy_recurrent_window_days": 14,
    # Confounder-Sieb
    "confounders": {
        "temp_c_hot_threshold": 22,    # >= 22 °C -> Meldung flankieren
                                        # (Hitze-Grenze aus
                                        # heat-pace-penalty-at-fixed-hr.md)
        "outdoor_corridor_floor_adjust": -1,  # CR10 auf Floor bei Outdoor
        "decoupling_max_pct": 10,      # > 10% -> HF-2. Hälfte nicht nutzen
                                        # (Anker: compliance-decoupling-
                                        # thresholds.md)
        "hr_data_quality_required": "ok",  # sonst Check aussetzen
    },
}


def rpe_hr_discrepancy_check(block, activity, context):
    """
    Emits a finding of one of:
      - None (no signal)
      - "RPE_LOW_PRIMARY"     (Verdacht, Meldung wert)
      - "RPE_LOW_STRONG"      (Band-Rekalibrierungs-Verdacht)
      - "RPE_HIGH_RECURRENT"  (Readiness-Verdacht)
    plus context on which confounders were checked.
    """
    cfg = RPE_CHECK_DEFAULTS

    # 1) Qualifikation
    if block.duration_min < cfg["min_block_min"]:
        return None
    if block.start_offset_min < cfg["activity_start_buffer_min"]:
        return None
    if activity.hr_data_quality != cfg["confounders"]["hr_data_quality_required"]:
        return None
    if block.rpe_cr10 is None:
        return None  # kein RPE zurückgemeldet -> Check nicht anwendbar
    if block.pct_lthr is None:
        return None

    # 2) Korridor auflösen
    floor, ceiling = None, None
    for _key, (lo, hi, f, c) in cfg["corridor"].items():
        if lo <= block.pct_lthr <= hi:
            floor, ceiling = f, c
            break
    if floor is None:
        return None  # Block ausserhalb definierter %LTHR-Bereiche

    # 3) Confounder-Adjustierung
    if activity.surface != "treadmill":
        floor += cfg["confounders"]["outdoor_corridor_floor_adjust"]
    if context.weather.temp_c is not None and \
       context.weather.temp_c >= cfg["confounders"]["temp_c_hot_threshold"]:
        # Hitze: Check kann feuern, aber Meldung wird als
        # "hitze-flankiert" markiert und in der niedrigen Richtung
        # deutlich abgeschwächt (Hitze senkt RPE meist NICHT, hebt HF -
        # in der Kombination wird der Check *konservativer*, nicht heisser)
        floor -= 1  # zusätzlicher Puffer
    if block.decoupling_pct is not None and \
       block.decoupling_pct > cfg["confounders"]["decoupling_max_pct"]:
        # HR 2. Hälfte unbrauchbar: HF-1. Hälfte re-benutzen
        block = block.with_hr(block.hr_first_half)
        # (%LTHR neu berechnen und Korridor neu auflösen - hier verkürzt)

    # 4) Vergleich
    delta_low  = floor    - block.rpe_cr10  # positiv = RPE UNTER Floor
    delta_high = block.rpe_cr10 - ceiling   # positiv = RPE ÜBER Ceiling

    # 5) Auslöser
    if delta_low >= cfg["low_discrepancy_strong_single"]:
        return ("RPE_LOW_STRONG", {"delta": delta_low, "block": block})
    if delta_low >= cfg["low_discrepancy_primary"]:
        # Wiederholungs-Verstärkung prüfen (aus Athletendaten-Historie)
        n_recent = count_recent_low_primaries(
            athlete=activity.athlete,
            window_days=cfg["low_discrepancy_strong_recurrent_window_days"],
        )
        if n_recent + 1 >= cfg["low_discrepancy_strong_recurrent_count"]:
            return ("RPE_LOW_STRONG", {"delta": delta_low,
                                        "recurrent_n": n_recent + 1})
        return ("RPE_LOW_PRIMARY", {"delta": delta_low, "block": block})

    if delta_high >= cfg["high_discrepancy_primary"]:
        n_recent = count_recent_high_primaries(
            athlete=activity.athlete,
            window_days=cfg["high_discrepancy_recurrent_window_days"],
        )
        if n_recent + 1 >= cfg["high_discrepancy_recurrent_count"]:
            return ("RPE_HIGH_RECURRENT", {"delta": delta_high,
                                            "recurrent_n": n_recent + 1})

    return None
```

### Downstream-Verwendung (Vorschlag — Vorlage für den Head-Coach)

1. **`RPE_LOW_PRIMARY`** — als **INFO** in `dataWarnings` oder als Zeile
   in `coach-analyst`-Output (analog zum Decoupling-Hinweis). Text-
   vorschlag: *„Block war ~X CR10 leichter als für Y % LTHR erwartet —
   einzelnes Signal, noch kein Rekalibrierungs-Anlass. Beobachten."*
2. **`RPE_LOW_STRONG`** — als **WARNING** und als expliziter
   **Rekalibrierungs-Trigger** für die %LTHR-abgeleiteten Bänder in
   `config/athlete_status.md`. Text: *„Y % LTHR-Band scheint zu tief
   angesetzt (RPE ~X CR10 unter Korridor über N Einheiten). Nächster
   Schwellentest empfohlen; bis dahin Bänder um ~5 % LTHR nach oben
   probeweise verschieben."*
3. **`RPE_HIGH_RECURRENT`** — Routing in den bestehenden
   `combinedOverloadSignal`-Pfad (HRV+RHR+RPE-Trio) und in den
   Mental-Coach-Trigger. **Keine** Band-Rekalibrierung.

### Konkrete Datei-Änderungen (VORSCHLÄGE, nicht angewendet)

* **`framework/config.example/training_paradigms.md`** — Abschnitt
  „RPE-Korridor pro %LTHR-Band" ergänzen (die Tabelle aus TL;DR §2),
  mit Verweis auf dieses Dokument.
* **`framework/agents/coach-analyst.md`** — im Kontrakt einen Absatz
  ergänzen, der den `RPE_LOW_PRIMARY`/`RPE_LOW_STRONG`-Signal-Output
  spezifiziert (analog zum bestehenden Decoupling-Absatz).
* **`framework/CLAUDE.md`** — die *rehearsal-below-expectation*-Klausel
  („A rehearsal that comes back far easier than the band predicts is
  evidence against the band") um einen Verweis auf diesen Check und
  seine Schwellen ergänzen, damit die Klausel operationalisiert und
  mechanisch prüfbar wird.
* **`framework/scripts/validate_plan.py`** — kein direktes Regel-
  Äquivalent (der Check ist analyse-, nicht plan-zeitig); ein
  post-activity-Analog wäre in `scripts/audit_consistency.py` als
  neuer Checker (`RPE_HR_DISCREPANCY`) sinnvoller.
* **`framework/config.example/athlete_status.md`** — den
  `rpe_check`-Block als optionale Konfiguration dokumentieren (Defaults
  wie im Pseudo-Code oben, per Athlet überschreibbar analog
  `impact_streak_max`).

## Open questions / Caveats

1. **Der Extrapolations-Schritt „~1 CR10 pro ~10 % LTHR" ist eine
   Coach-Konvention**, nicht direkt studien-belegt. Nur die Endpunkte
   (LT ≈ CR10 3, IAT/LTHR ≈ CR10 5) sind aus Scherr 2013 punktuell
   abgesichert; die Bänder für ~85–89 % LTHR und ≥ 103 % LTHR sind
   extrapoliert. Der Korridor sollte deshalb als **grobe Richtungsgrösse**
   behandelt und nicht zur Feinjustage einzelner %-Punkte benutzt werden.
2. **Populations-Referenz vs. individueller Anker.** Die SDs kommen aus
   heterogenen Kohorten (Scherr N = 2 560 gemischt). Der reale Ziel-Athlet
   liegt irgendwo im Korridor, aber ***wo* er liegt, wissen wir erst nach
   ein paar sauberen Referenz-Sessions**. Ein Athlet, der reproduzierbar
   am unteren Rand des Korridors rated (z. B. „ich melde für Threshold
   immer CR10 4–5, nicht 5–7"), löst mit den Default-Schwellen ständig
   Fehlalarme aus. **Zwei-Stufen-Kalibrierung sinnvoll:**
   - **Baseline-Phase:** die ersten 4–6 qualifizierenden Blöcke werden nur
     *geloggt*, nicht *gemeldet* — daraus wird der athleten-spezifische
     Erwartungs-Punkt (Median RPE) je %LTHR-Band abgeleitet.
   - **Steady-State:** Diskrepanz wird gegen den athletenspezifischen
     Median (± 2 SD) statt gegen den Populations-Korridor gemessen.
   Das framework hat die Infrastruktur dafür in
   `data/muscles/*.jsonl` bzw. den Activity-Logs; ein
   `athlete_rpe_baseline.json` wäre naheliegend.
3. **Session-RPE vs. Segment-RPE.** Die Literatur zu RPE-an-LT (Scherr,
   Kang) misst *während* der Belastung (Segment-RPE). Die framework-
   Praxis liest oft *session-RPE* (post-workout, single number nach
   Foster 2001), die den härtesten Teil überproportional gewichtet. Bei
   Einheiten mit **einem** dominanten Quality-Block ≥ 8 min fällt das
   nicht ins Gewicht; bei Einheiten mit mehreren Quality-Blöcken (z. B.
   4×8 min Threshold + Easy) ist die Zuordnung Session-RPE→einzelner
   Block-%LTHR nicht sauber. **Empfehlung:** Check läuft nur, wenn
   entweder Segment-RPE explizit vorliegt oder die Einheit strukturell
   ein-Block ist.
4. **Kein Studien-Nachweis für die exakte Schwelle „≥ 2 CR10 unter
   Korridor".** Die Schwelle ist aus SD (interindividuell) und SEM
   (test-retest) abgeleitet, aber **nicht** in einer Interventions-
   Studie validiert. Die Wahl ist konservativ und begründet, aber
   revidierbar — nach 3–6 Monaten Betrieb kann anhand der Alarm-
   Ausbeute (True/False-Positive-Rate) nachkalibriert werden.
5. **Der Check ist blind für „richtige Vorgabe, aber falscher Athleten-
   Zustand"** — z. B. Übermotivation im Rennen (RPE unter Erwartung, HF
   real hoch, Band richtig, Athlet pusht) vs. Underperformance (RPE
   hoch, HF niedrig, Band richtig, Athlet ermüdet). Deshalb ist das
   Signal ein **Verdacht**, nicht eine Zuweisung; der Coach muss die
   Kandidat-Erklärungen (Band vs. Zustand vs. Confounder) im Ergebnis-
   Text explizit auseinanderhalten.
6. **HF könnte durch NGP/Pace/Power gestützt werden** (siehe Findings §6).
   Ein v2 des Checks könnte parallel eine NGP-vs-RPE-Diskrepanz laufen
   lassen und die beiden Signale konjunktiv ("beide sagen zu leicht") vs.
   disjunktiv ("nur eines") auswerten — das würde die False-Positive-Rate
   weiter senken. Erfordert aber saubere NGP-Anker in
   `athlete_status.md`, die derzeit weniger belastbar sind als LTHR.
7. **Skala-Diskrepanz** zwischen Borg CR10 (0–10) und Borg 6–20 in der
   Literatur ist zwar durch die Umrechnung Borg 6–20 ≈ (CR10 × 2) + 6
   grob abbildbar, aber **nicht 1:1**. Die Empfehlung ist, im framework
   konsequent **CR10** zu verwenden (wie im Isometrie-Doc), und die
   Konvertierung nur beim Zitieren von Studien vorzunehmen — nicht
   umgekehrt.
