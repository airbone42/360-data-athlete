# HM race HR vs. training HR — target vs. guardrail for half-marathon-pace work

**Erstellt:** 2026-06-20

## TL;DR

A maximal half-marathon (HM) is run at threshold-region intensity, in HR
terms typically settling around **~88–92 %LTHR (~86–90 %HRmax)** in the
first third, climbing to **~95–98 %LTHR** in the final third via cardiac
drift, for an event-average around **~93–95 %LTHR**. Training HR-pace
work should therefore **pace-lead with HR as a guardrail, not target
race HR**: on short, fresh blocks (2–3 km, fresh legs, cool start) HR
during a true HM-pace effort sits a few bpm BELOW race HR because
neither drift nor pre-race sympathetic arousal has accumulated;
chasing race HR on such a rep forces pace **above** real HM pace and
mis-trains the stimulus. On long continuous HM-pace blocks (8–12 km off
fatigue) HR converges toward race HR and the guardrail moves up
accordingly. Encode the HR ceiling as a **duration-dependent band**,
not a single value.

## Question / Trigger

Auslöser: ein dokumentierter Vorfall aus realer Anwendung — der Coach
hatte für HM-Pace-Trainingsblöcke eine HR-Decke nahe ~94 %LTHR
verwendet, und es war unklar, ob dieses Limit (a) richtig kalibriert
oder (b) konzeptionell falsch konstruiert ist, weil es Trainings-HR
und Renn-HR gleichsetzt. Konkrete Fragen:

1. Läuft die HF im Wettkampf bei gleicher Pace/RPE höher als im
   Training, und in welcher Größenordnung?
2. Welche HR-Bands (%LTHR, %HRmax) hält ein gut trainierter Athlet im
   HM tatsächlich aus, und wie sieht das Within-Race-Drift-Muster aus?
3. Soll ein HM-Pace-Trainingsblock die **Renn-HF** als Ziel haben,
   oder die **Pace** führen und die HF als Guardrail unterhalb der
   Renn-HF setzen?
4. Hängt das HR-Target von der Blocklänge (kurz/frisch vs.
   lang/erschöpft) ab?

## Findings

### 1. Race HR vs. training HR at matched pace/effort

Mehrere unabhängige Mechanismen heben die HF im Wettkampf gegenüber
einem identischen Trainings-Bout an:

- **Anticipatory / pre-start sympathetic arousal.** Vor dem Wettkampf
  steigen Cortisol, LF/HF-Ratio und Baseline-HF messbar an
  (Anticipatory Response, Cerutti et al. 2018). Die sympathische
  Dominanz reicht in die ersten Wettkampfminuten hinein und hebt die
  HF bei jeder gegebenen Pace.
- **Katecholamine im Wettkampf.** Wettkampf-Erregung (Adrenalin/
  Noradrenalin) verstärkt sympathische Aktivierung über das hinaus,
  was die rein metabolische Last erklärt (Cardiac Vagus & Exercise,
  APS Physiology 2019).
- **Cardiac drift über die Distanz.** Plasmavolumen sinkt 3–5 % über
  die Renndauer, Stroke Volume fällt, HF steigt 5–15 bpm, um Cardiac
  Output konstant zu halten — dieser Effekt akkumuliert mit Dauer und
  Hitze (Coyle 1998; Marathonhandbook-Synthese).
- **Hitze/Dehydratation/Glykogendepletion** addieren sich zur Drift.

**Typische Größenordnung** im Marathon/HM: nach den ersten 5 km
stabilisiert sich %HRmax bei einer Marathonleistung um 88–91 %HRmax
(Esteve-Lanao et al., PMC9566186), aber innerhalb des Bouts driftet HF
weiter, während Pace und %VO₂max bereits sinken — d. h. HF
**unterschätzt nicht** den metabolischen Stress; sie überzeichnet ihn
sogar im späten Renndrittel. Konkret bedeutet das: dieselbe Pace,
mehrere bpm Differenz zwischen frischem Trainings-Bout und
Wettkampfminute 60+.

### 2. HM race intensity in HR terms (band + within-race pattern)

In Joe Friels LTHR-basierten Laufzonen (TrainingPeaks-Tabelle) liegt
die nachhaltige HM-Race-Intensität fast vollständig **in Zone 4
(95–99 %LTHR)** im Schnitt, mit einem Anfangsdrittel in **oberer Zone 3
(90–94 %LTHR)** und einem Endspurt-Drift in **untere Zone 5a (100–102
%LTHR)**.

Operatives Band, das die Literatur und der Drift-Mechanismus
gemeinsam tragen:

| Renn-Phase | %LTHR | %HRmax (≈) | Logik |
|---|---|---|---|
| Start (0–5 km, gut gepaced) | ~88–92 % | ~86–90 % | Settle unterhalb Threshold; Pre-Start-Arousal klingt ab |
| Mitte (5–15 km) | ~93–96 % | ~89–92 % | Pace stabil, HF driftet langsam |
| Endspurt (final ~3–5 km) | ~96–100 % | ~92–95 % | Drift + finaler Kick, kurz über LTHR akzeptabel |
| Peak (letzter km) | ≤ ~102 % | ≤ ~96 % | „Spike erlaubt", aber Kosten steigen super-linear |
| **Event-Mittel** | **~93–95 %** | **~89–92 %** | gut gepaceter, maximaler HM |

Der **Within-Race-Drift** ist ein robuster Befund: Erstes Halb
durchschnittlich ~3–5 bpm unter dem Endspurtmittel bei gleicher oder
sogar leicht *langsamerer* Pace — das ist Drift, nicht „Athlet hat
nachgelegt".

Empirischer Anker aus realer Anwendung (Pattern, nicht Athlet): Ein
maximaler, gleichmäßig gepacter HM in kühlen Bedingungen produzierte
1. Halb 152.8 vs. 2. Halb 157.3 = **+4.5 bpm Drift bei nahezu
identischer Pace**, Peak im finalen km ≈ 98 %LTHR, Event-Mittel ≈
93–94 %LTHR. Das deckt sich exakt mit dem Friel-Z4-Band.

### 3. Prescriptive implication — target vs. guardrail (the actual decision)

**Pace führt, HF ist Guardrail — nicht umgekehrt.** Die HF in einem
HM-Pace-Trainingsblock soll **NICHT** die im Wettkampf gesehene HF
**targetieren**. Begründung:

- Im Training fehlt die Pre-Start-Sympathik (Punkt 1) — bei *gleicher
  HM-Pace* fällt die HF im Training systematisch niedriger aus.
- Drift akkumuliert über die Renndauer. Ein 2–3 km Trainingsbout aus
  frischen Beinen erreicht die HF des Renn-Minute-70 schlicht nicht,
  ohne **über** HM-Pace zu laufen.
- Wer in einem kurzen, frischen Bout die Renn-HF „chased", **überholt
  die HM-Pace** — d. h. er trainiert oberhalb der Schwelle (Z4+) statt
  unter ihr, mis-trainiert den Stimulus und kostet Erholung.

**Korrekte Kodierung der HR-Decke** (Guardrail-Modell):

1. **Pace ist primär.** Ziel-Pace ist die geplante HM-Pace (oder das
   pace-äquivalente Power-Band auf dem Rad). Der Athlet läuft Pace,
   nicht HF.
2. **HF-Decke ist duration-dependent**, nicht ein single value:
   - **Kurzer/frischer Block (2–4 km, fresh, kühl, früh in der
     Session):** Decke ~88–93 %LTHR. Bei Pace=HM-Pace darf die HF
     mehrere bpm unter Renn-HF liegen — das ist korrekt, nicht
     „underperformance".
   - **Mittlerer Block (4–8 km):** Decke ~92–96 %LTHR. Drift beginnt,
     HF nähert sich dem Renn-Mittel.
   - **Langer kontinuierlicher Block (8–12 km, off fatigue,
     Race-Simulation):** Decke ~94–98 %LTHR — konvergiert auf das
     Renn-Mittel, weil Drift jetzt auch im Training akkumuliert ist.
3. **Decke schaltet auf Pace, nicht auf HR, wenn beide kollidieren.**
   Wenn HF die Decke trotz korrekter Pace bei kühlen Bedingungen
   reißt, ist das ein **Signal** (Hitze, Müdigkeit, Krankheit), kein
   Auto-Slowdown — der Coach wertet es aus, der Athlet entscheidet
   nicht Mid-Bout aus der HF heraus zu drosseln, solange Pace und RPE
   stimmen. Kühle, frische Bedingungen + Pace-Halt + HF unter Decke =
   Stimulus landet richtig.
4. **Kein Auto-Slowdown bei HF unter Decke.** Eine HF, die im frischen
   Block unter Renn-HF bleibt, ist **kein** Anlass, Pace anzuheben —
   das wäre der „chase race HR"-Fehler.

### 4. Duration / length dependence of the HR target

Die HF-Decke ist **eine Funktion der Blocklänge**, weil Drift mit
Dauer akkumuliert. Konkret:

- **2–3 km fresh:** HF liegt 4–8 bpm unter Renn-Mittel — das ist
  erwartet, nicht Defizit.
- **5–6 km:** HF nähert sich Renn-Mittel von unten.
- **8–12 km kontinuierlich:** HF erreicht oder überschreitet Renn-
  Mittel; Decke darf bis nahe LTHR (100 %) reichen, weil das die
  echte Race-Simulation ist.

Eine **statische** HR-Decke (z. B. „immer ≤ 94 %LTHR auf HM-Pace") ist
fehl-konstruiert: sie ist zu hoch für den kurzen frischen Bout (lädt
zum Über-Pacing ein) und zu niedrig für den langen Block off fatigue
(droht echten Race-Sim-Stimulus zu kappen, wenn HF natürlich driftet).

## Primary sources

| Title | Authors | Year | Journal/Link | Key quote (paraphrased) |
|---|---|---|---|---|
| Heart Rate Does Not Reflect the %VO₂max in Recreational Runners during the Marathon | Esteve-Lanao et al. | 2022 | *Int. J. Environ. Res. Public Health* / [PMC9566186](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9566186/) | %HRmax stabilises at 88–91 % after the 5th km but progressively decouples upward from %VO₂max because of cardiovascular drift — HR overstates the metabolic load late in the race. |
| Pacing Strategy Affects the Sub-Elite Marathoner's Cardiac Drift and Performance | Díaz et al. | 2019 | *Frontiers in Psychology* / [PMC7043260](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7043260/) | Cardiac drift over a sustained race is a function of pacing: even-paced efforts show measurable HR rise from first to second half at identical or slightly slower pace; aggressive early pacing magnifies the drift and hurts final performance. |
| Cardiac Vagus and Exercise | Gourine & Ackland | 2019 | *Physiology (APS)* / [journals.physiology.org](https://journals.physiology.org/doi/full/10.1152/physiol.00041.2018) | At ~140 bpm sympathetic and parasympathetic influences are approximately balanced; above that sympathetic dominance grows. Psychological arousal in competition shifts the balance further toward sympathetic activation, raising HR at any given workload. |
| Anticipatory response before competition (autonomic / cortisol pre-race elevation) | Cerutti et al. | 2018 | *PLOS One* / [PMC6072081](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6072081/) | Pre-race cortisol and LF/HF ratio are significantly higher than pre-training baselines — pre-start sympathetic tone elevates HR before the event has begun. |
| Pre-Anticipatory Anxiety and Autonomic Nervous System Response to Fitness Competition Workouts | — | 2019 | [PMC6784172](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6784172/) | Moderate-to-large HR elevations are observed prior to competition workouts vs. training, with sustained sympathetic activation. |
| Joe Friel's Quick Guide to Setting Zones (running) | Joe Friel | — | [trainingpeaks.com](https://www.trainingpeaks.com/learn/articles/joe-friel-s-quick-guide-to-setting-zones/) | Running zones expressed as %LTHR: Z3 = 90–94, Z4 = 95–99, Z5a = 100–102. HM race intensity for a trained athlete sits in upper Z3 → Z4 average, with Z5a only in the final kick. (Recognised coach source, used here because the %LTHR convention used by intervals.icu/TrainingPeaks descends from this framework.) |
| Marathon heart-rate zone / drift synthesis | Marathon Handbook | — | [marathonhandbook.com](https://marathonhandbook.com/marathon-heart-rate/) | Cardiovascular drift of 5–15 bpm over 90 min is normal in moderate conditions; HR should be used to flag catastrophic deviation, not to fine-control pace. (Coach source — used for the practical synthesis, not as primary evidence.) |

## Application in framework

The following framework-level paradigm wording should change. Each is
phrased generically; athlete-specific HR-bpm numbers are derived in
`config/` from each athlete's current LTHR.

1. **`framework/config.example/training_paradigms.md`** —
   HM-pace / threshold-block prescription must state:
   - Pace leads, HR is a guardrail (not a target).
   - The HR ceiling is **duration-dependent**: short/fresh block sits a
     few bpm below race HR; long continuous block converges to race
     HR. Suggested band table:
     - 2–4 km fresh: ≤ ~88–93 %LTHR
     - 4–8 km: ≤ ~92–96 %LTHR
     - 8–12 km continuous: ≤ ~94–98 %LTHR
   - Explicit anti-pattern callout: "chasing race HR on a short fresh
     rep forces pace above HM pace and mis-trains the stimulus —
     forbidden."

2. **`framework/agents/specialist-endurance.md`** —
   Add a "HM-pace block HR encoding" section:
   - Specialist MUST emit pace as primary target on HM-pace work.
   - HR field is `cap` / `≤ X %LTHR`, **not** `target = race HR`.
   - The cap value is selected from the duration-band table above
     based on the block's continuous length.
   - When the athlete's race HR profile is known
     (`config/athlete_status.md` → race HR by race phase), the
     specialist may tighten the long-block cap to that athlete's
     observed race average + drift band, but never below the
     duration-band floor.

3. **`framework/agents/coach-analyst.md`** —
   Add a "do not flag HR-below-race-HR on short HM-pace reps as
   underperformance" clause (parallel to the existing "minute-0–10
   spike is a kinetics artifact, not a finding" rule). When pace was
   on target and the block was short/fresh, HF below race-HR mean is
   **expected**, not a coaching finding.

4. **`framework/research/README.md`** index — new row added.

Athlete-individual application (the specific bpm numbers per band,
the athlete's observed HM race-HR profile, the durability/fatigue
caveat for the long block) lives in the wrapper's `config/` —
`athlete_status.md` (LTHR + race-HR profile) and `competition_plan.md`
(taper / race-simulation block prescriptions).

## Open questions / Caveats

- The %LTHR bands above assume an **accurately calibrated LTHR**
  (recent race-validated, not formula-derived). When the LTHR anchor
  itself is stale, the bands shift in absolute bpm. Athlete-side
  calibration cadence (race-validated LTHR refresh) is a separate
  question.
- Heat / dehydration / altitude amplify drift beyond the bands
  above. The duration-dependent ceiling should be widened, not
  enforced harder, in such conditions — or the block converted to a
  pace-only prescription with HR purely descriptive.
- The "chase race HR" anti-pattern is specific to **threshold-region**
  training (HM-pace, MP-pace, tempo). It does NOT apply to VO₂max
  intervals, where HR lags VO₂ kinetics anyway and the pacing variable
  is pace/power, not HR — but the failure mode there is the
  warm-up-priming question, not race HR (see
  `warmup-priming-intervals.md`).
- Within-race drift magnitude has athlete-individual variance (plasma
  volume, sweat rate, fitness, fueling). The +4–6 bpm pattern is
  typical; +8 bpm under heat stress is also normal. The band table
  treats this as a band, not a point.
- The literature is dominated by marathon-distance studies; HM-specific
  HR-profile studies are sparser. The bands derive HM from
  marathon-minus-distance-effect plus Friel's threshold-zone
  convention plus practical race-HF traces — defensible, not airtight.
