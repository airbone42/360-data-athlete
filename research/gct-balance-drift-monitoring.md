# Ground-Contact-Time-Balance-Drift im Dauerlauf — Frühindikator oder Rauschen?

**Erstellt:** 2026-07-25

## TL;DR

Die Literatur trägt **keine validierte absolute Schwelle** für die
GCT-/Stance-Time-Balance als in-run Frühindikator einer einseitigen
Überlastung. Gesunde Läufer zeigen im Mittel < 4 % Asymmetrie
(Vincent 2025, N=250), und in der einzigen großen prospektiven Kohorte
(Malisoux 2024, N=836, 6 Mo Follow-up) war eine erhöhte
Kontaktzeit-Asymmetrie **nicht** mit einem höheren Verletzungsrisiko
verknüpft (p=0.087). Messseitig ist die absolute GCT-Sensorik am
Handgelenk/Brustgurt mit substanziellem Gerätefehler behaftet
(Drobnič 2023: 80–120 ms Bias vs. 3D-MoCap), womit auch das abgeleitete
Balance-Verhältnis ein nicht triviales Rauschband trägt. **Operative
Konsequenz:** in-run-Balance-Drift bleibt eine **deskriptive
Beobachtungsgröße**, kein Abbruch-Trigger. Symptom-basiertes
Stop-Kriterium bleibt der primäre Anker. Die FIT-Feld-Konvention
(`stance_time_balance`) ist **hersteller-/firmware-abhängig und in der
SDK-Doku nicht eindeutig festgelegt** — sie ist per empirischem
Lastprotokoll (bewusst einseitige Belastung, siehe unten) zu verifizieren.

## Question / Trigger

Auslöser: coach-geflaggte Unsicherheit aus realer Anwendung — im
Dauerlauf-Kontext (aerobe Intensität, konstante Pace) zeigt die
Ground-Contact-Time-Balance eines schuh-/brustgurt-basierten
Running-Dynamics-Sensors eine progressive Verschiebung von einem
stabilen ~50/50-Fenster in Richtung einer Seite, während GCT,
Schrittlänge und Kadenz pace-normalisiert keine Auffälligkeit zeigen.
Das subjektive einseitige Symptom (Zwicken TFL/IT-Band) folgt der
mechanischen Verschiebung mit Verzögerung.

Sechs Teilfragen:

1. **Messgüte** der GCT-/Stance-Time-Balance aus Wearable-Sensorik
   (Test-Retest, MDC, Tagesform-Streuung, Rausch-Untergrenze).
2. **Normalbereich** und Ruhe-Asymmetrie bei Gesunden — hat die
   Ruhe-Asymmetrie eigenständigen Risikowert, oder nur die
   ermüdungsinduzierte Änderung?
3. **Ermüdungs-Dynamik** — driftet die Kontaktzeit-Symmetrie über einen
   langen Lauf ohnehin, und in welcher Größenordnung? Ohne Vergleichs-Drift
   bei Gesunden ist ein beobachteter Drift nicht interpretierbar.
4. **Prognostischer Wert** — prospektive Verknüpfung von
   belastungsinduzierter Asymmetrie-Zunahme mit späterer einseitiger
   Überlastung (ITB, TFL, Stressreaktion)? Speziell: eigenständiger Wert
   einer **fehlenden Normalisierung nach Belastungsende**?
5. **FIT-Feld-Konvention** — Definition von `stance_time_balance`
   (L%- oder R%-Anteil, geräteabhängig?) und wie ein Anwender die
   Konvention **empirisch** verifiziert.
6. **Praktische Ableitung** — falls die Evidenz eine Schwelle hergibt:
   welche, gemessen woran; falls nicht: deskriptives Monitoring-Protokoll.

## Findings

### Q1 — Messgüte: substanzielle absolute Fehler, Balance-Ratio inheritiert die Rauschbasis

- **Drobnič et al. 2023 (Sensors 23(16):7155)** verglich den Garmin
  Running Dynamics Pod mit 3D-MoCap: der Pod **unterschätzte** die
  absolute Bodenkontaktzeit um **−81 bis −120 ms** über verschiedene
  Schrittfrequenzen; Limits of Agreement zwischen 72 und 111 ms.
  Die Bias-Größenordnung schrumpft bei höheren Schrittfrequenzen.
  Kontext-Caveat: das Protokoll war „running in place" (nicht
  vorwärts) — die Absolut-Bias mag im normalen Vorwärtslauf niedriger
  sein, aber die Rauschebene bleibt substanziell.
- **Roell et al. 2015 (Myotest, PMC4415832)** dokumentierte für ein
  vergleichbares Wearable moderate Test-Retest-Reliabilität für GCT
  nur bei ~14 km/h und **schlechte** Reliabilität bei 10–12 km/h; auch
  hier signifikante Abweichungen gegen Kraftplatten.
- **Konsequenz für die Balance-Ratio:** ist die absolute GCT mit ±10 %
  Bias behaftet, ist die daraus abgeleitete L/R-Balance nicht direkt
  präziser — Absolut-Fehler sind zwar links/rechts korreliert (fällt
  teilweise raus), aber Elektroden-/Sensorlage-Drift, Strap-Slip und
  Schrittfrequenz-abhängige Detektions-Latenz produzieren
  seitenungleiche Fehler. Eine belastbare Test-Retest-Studie
  speziell für den **Balance-Kanal** in feld-relevanten Bedingungen
  fehlt in der Peer-Reviewed-Literatur.
- **Praktische Rausch-Untergrenze:** Garmins eigenes drei-Stufen-Rating
  (Good ≤ 50.7 %, Fair 50.8–52.2 %, Poor > 52.2 % — ⚠️ Zitat-Audit 2026-09-01: die Zahlen stimmen, Garmin liefert sie aber als Tabelle mit getrennten L/R-Zeilen, nicht als zusammenhängenden Satz; die Anführungszeichen sind entfernt, weil sie einen Originalwortlaut suggerierten) ist eine
  populations-perzentile Einteilung, **keine** validierte
  Fehler-/Signalgrenze. Sie taugt für eine grobe „ist der Wert
  überhaupt auffällig"-Frage, aber nicht als Abbruch-Schwelle.

### Q2 — Normalbereich und Asymmetrie bei Gesunden: klein und ohne prospektiven Risikowert

- **Vincent et al. 2025 (Frontiers in Sports and Active Living, N=250
  verletzungsfreie Läufer 15–75 J)**: „Spatiotemporal asymmetries
  were generally low at < 4 % among all runners, irrespective of age."
  Rechts-Links-Differenz der Stance-Time ~0.004–0.006 s. Alter hatte
  keinen substanziellen Effekt (η² = 0.035–0.040).
- **Malisoux et al. 2024 (BMJ Open Sport & Exerc Med, N=836
  Freizeitläufer, 6-Monats-Follow-up, 107 Verletzungen)**: Median
  Symmetry-Index für Kontaktzeit **1.7 % (IQR 0.7–2.9 %)**. Die
  Kontaktzeit-Asymmetrie war in Cox-Regression **nicht** mit dem
  Verletzungsrisiko assoziiert (crude p=0.087, adjusted p=0.069).
  Höhere Flugzeit- und Peak-Bremskraft-Asymmetrie war sogar mit
  **niedrigerem** Risiko assoziiert.
- **Life 2026 (systematic review) / Malisoux 2024 (Diskussion)**: die
  populär angenommene „Asymmetrie > 10–15 % ist pathologisch"-Schwelle
  hat keine Grundlage in prospektiver Läufer-Kohorten-Evidenz — sie
  stammt aus Return-to-Sport-Literatur zu Explosivkraft-Asymmetrien
  nach Verletzung.

Die entscheidende Frage ist damit nicht der **absolute Asymmetriewert**
bei Baseline (der ist bei Gesunden im schmalen Band und prognostisch
irrelevant), sondern die **dynamische Veränderung unter Belastung** —
Teilfrage Q3.

### Q3 — Ermüdungs-Dynamik: uneinheitlich, mit hoher inter-individueller Streuung

- **Gao et al. 2022 (Frontiers in Physiology, N=18 männliche
  Amateurläufer, treadmill-Ermüdungsprotokoll bis Erschöpfung)**: nach
  Ermüdung stieg die Asymmetrie in **Kniestreckwinkel (+17 %),
  Knie-Abduktions-Moment (+10 %), Hüft-Flexionsmoment (+11 %)**.
  **Stance-Time-Symmetrie war nicht das primäre Outcome** — die
  Ermüdungswirkung auf Gelenk-Moment-Asymmetrie war deutlich stärker
  als auf spatiotemporale Parameter.
- **Systematic Review Life 2026 (PMC12942261)**: „Fatigue increased
  asymmetry in knee and hip joint moments and angles, particularly in
  coronal and transverse planes." Die Autoren räumen ein: „few studies
  directly linked biomechanical changes to injury outcomes,
  necessitating cautious interpretation of injury relevance."
- **Absolute GCT** verlängert sich bei Ermüdung reproduzierbar bei
  beiden Beinen — reflektiert reduzierte neuromuskuläre Effizienz
  (Fatigue-Related Changes, Frontiers 2021, PMC7926175). Ob sich das
  L/R-Verhältnis dabei systematisch verschiebt, hängt vom Individuum
  ab; **es gibt keinen dokumentierten „normalen Drift" bei Gesunden
  über 60–90 min Dauerlauf** in der öffentlichen Literatur, gegen den
  ein beobachteter Drift verglichen werden könnte.
- **Trainierte Läufer** zeigen laut Royal Society Open Science 2026
  (250668) „high durability … preserving biomechanical stability and
  running efficiency despite increasing perceived fatigue" — d.h. der
  erwartete Grundrausch-Drift ist bei trainierten Ausdauerläufern
  eher **klein**, was den Signal-Rausch-Abstand für einen echten
  Individual-Drift verbessert.

Die entscheidende Kontroll-Frage („was ist der normale Drift bei
Gesunden?") ist damit in der Literatur **nicht beantwortbar mit einer
belastbaren Zahl**. Die einzige verfügbare Baseline ist die
**athleten-individuelle** aus den ersten 15–25 min desselben Laufs.

### Q4 — Prognostischer Wert: theoretischer Pfad, keine kausalen Prospektiv-Daten

- **Malisoux 2024** ist die stärkste verfügbare prospektive Evidenz
  spezifisch für die Kontaktzeit-Asymmetrie — mit **negativem
  Ergebnis**.
- **Life 2026 (systematic review)**: „The majority of studies included
  in this review … did not prospectively track injury incidence.
  Accordingly, these variables should be interpreted as biomechanical
  correlates or theoretical pathways that may contribute to injury
  development rather than causal predictors."
- **Zur spezifischen Frage „fehlende Normalisierung nach
  Belastungsende hat eigenständigen prognostischen Wert"**: keine
  Studie identifizierbar, die diese Frage prospektiv untersucht hätte.
  Es gibt keine Publikationen, die post-run-Kontaktzeit-Balance nach
  Recovery-Zeit-X als Prädiktor verwenden. Diese Hypothese ist plausibel
  (persistierende Asymmetrie ~ persistierendes neuromuskuläres Defizit
  ~ höhere Wahrscheinlichkeit einer strukturellen Läsion), aber
  **empirisch nicht gestützt** in der aktuellen Literatur.
- **ITB-Syndrom-Prospektiv-Literatur** (Noehren, Ferber, Davis;
  ASB Award 2006 u.a.) identifiziert **Hüft-Adduktion, Knie-Innenrotation
  und Beckenkippung** als Risikoprofile — nicht GCT-Balance. TFL-Überlastung
  ist mechanistisch mit Beinlängendifferenz und Fuß-Typ (Supinator)
  assoziiert, nicht mit einer Kontaktzeit-Metrik.

**Zwischenfazit:** Ein beobachteter GCT-Balance-Drift ist ein
**hypothesengenerierender Befund**, keine diagnostische oder
prognostische Größe im evidenzbasierten Sinn. Als „Kanarienvogel im
Kohlebergwerk" für ein aufkommendes einseitiges Problem hat er
**plausible Face-Validity**, aber keine kalibrierte Sensitivität/Spezifität.

### Q5 — FIT-Feld-Konvention: hersteller-/firmware-abhängig, empirisch verifizieren

- **Garmin-Watch-Display (Manual, Ground Contact Time Balance Data)**:
  „If your data screen displays both numbers, for example 48–52, 48 %
  is the left foot and 52 % is the right foot." Das ist die
  **UI-Konvention** — L zuerst, R zweitens.
- **FIT-SDK-Rohfeld `stance_time_balance`** (Connect IQ API,
  `RunningDynamicsData`): dokumentiert als „Filtered instantaneous
  stance time percentage (0 – 100 %, 0.25 % precision)" — **die
  Seite wird nicht explizit definiert**. Die naheliegende Konvention
  ist, dass der Skalar die **linke** Seite in Prozent trägt (spiegelbild
  der UI-Anzeige), aber weder Connect-IQ-Doc noch FIT-SDK-Profile
  benennen das eindeutig; für den benachbarten Bike-Power-Kanal
  `left_right_balance` gibt es dagegen ein explizites Bit-Masking-Schema
  (MSB = Seite, 7 LSB = Wert), das für `stance_time_balance` **nicht**
  gilt (single scalar).
- **Es gibt daher keine belastbare Doku-Quelle**, die die Seite des
  `stance_time_balance`-Skalars für jede Geräte-/Firmware-Version
  garantiert. Die Konvention kann sich über Firmware-Versionen ändern
  (siehe Garmin-Forum-Threads zu „GCT Balance L/R missing since
  update 18.22").

**Empirische Verifikation (praktisch der wertvollste Teil):**

Zwei Test-Läufe von je 3–5 min bei aerober Konstant-Pace, mit
absichtlicher einseitiger Belastung, um zu erzwingen, dass **eine
Seite messbar länger Kontaktzeit hat**:

1. **Loaded-side-Test:** Hantel / Wasserflasche (2–3 kg) in **einer**
   Hand tragen, sonst normal laufen. Die belastete Seite bekommt
   längere Kontaktzeit (mehr Impuls, größere vertikale Kraft).
2. **Contralateral-lift-Test:** kleiner Fersen-Lift (5–8 mm Sohle,
   z.B. ausgetauschte Einlage) in **einem** Schuh. Die höhere Seite
   bekommt tendenziell **kürzere** Kontaktzeit, die tiefere längere.

Danach im FIT-File:

- Wenn Loaded-side = links → `stance_time_balance` > 50 %:
  **Skalar trägt L%.**
- Wenn Loaded-side = links → `stance_time_balance` < 50 %:
  **Skalar trägt R%.**
- Testtag mit Kontroll-Lauf ohne Belastung dazwischen, um sicherzugehen,
  dass die Verschiebung tatsächlich durch die Manipulation kommt und
  nicht durch Baseline-Drift.

Das ergibt eine **gerätespezifische, firmwarespezifische Konvention**,
die dokumentiert und beim nächsten Firmware-Update ggf. re-verifiziert
werden muss. Das ist die einzige Methode, die die Frage-Kette-Annahme
(„der Skalar bedeutet L%") aus der Interpretations-Kette entfernt,
ohne der Doku vertrauen zu müssen.

### Q6 — Praktische Ableitung: keine Schwelle, deskriptives Protokoll

Die Evidenzlage trägt **keine belastbare Abbruch- oder
Belastungs-Anpassungs-Schwelle** für GCT-Balance-Drift im Dauerlauf.
Weder ein absolutes Prozentband (z.B. „> 53 % ist Alarm") noch ein
Drift-Band gegenüber Baseline (z.B. „> 2.5 Prozentpunkte Verschiebung
gegenüber ersten 20 min ist Alarm") ist prospektiv validiert. Ein
mechanisches Stop-Kriterium auf Basis dieser Metrik wäre in der
Literatur nicht gedeckt.

**Empfohlenes deskriptives Monitoring-Protokoll (evidenzkonform):**

1. **Baseline pro Lauf:** Fenster min 5–25 (ersten 5 min GPS-/HR-Kaltstart
   verwerfen, 15 min stabiles Fenster mitteln → individuelle
   Baseline-Balance ± SD).
2. **In-run-Beobachtung:** rollierender 5-min-Median vs. Baseline.
   Ein Drift wird als **auffällig markiert** (nicht abbrechend), wenn:
   - **Größenordnung** ≥ **2 × Baseline-SD** (typisch 0.5–1.0 Prozentpunkte
     → Trigger bei ≥ 1.0–2.0 Prozentpunkte Verschiebung), **UND**
   - **Persistenz** ≥ 10 min (kein Einzel-Fenster-Ausreißer), **UND**
   - **Konsistenz mit sekundären Signalen** (Kadenz-Verlust,
     HR-Drift, subjektives Symptom, Schrittlängen-Verschiebung).
3. **Post-run-Beobachtung:** Balance-Wert in den letzten 5 min vor
   Belastungsende dokumentieren. Ob die Nicht-Rückkehr auf Baseline
   nach Ende der Belastung eigenständigen prognostischen Wert hat, ist
   **offen** (siehe Q4) — bis auf Weiteres als deskriptive
   Zusatz-Information mitloggen, **nicht** als eigener
   Alarm-Trigger.
4. **Aggregation über Läufe:** eine einmalige Beobachtung ist kein
   Signal. Erst wenn dasselbe Drift-Muster über **≥ 2–3 Läufe
   reproduzierbar** ist UND korreliert mit subjektiven Signalen auf
   derselben Seite, wird die Beobachtung zu einem Anlass, die
   Trainings-Belastung auf einseitige Muster (Schuh-Abrieb-Muster,
   Straßen-Camber, Kraft-Asymmetrie in einbeinigen Tests) zu prüfen.
5. **Primärer Stop-Trigger bleibt symptom-basiert** — ein einseitiges
   Zwicken, Ziehen, Schutzhaltung. GCT-Balance-Drift ist
   **ergänzende Information**, kein Ersatz.

## Primary sources

| Titel | Autoren | Jahr | Journal / Link | Zitat |
|---|---|---|---|---|
| Gait asymmetry in spatiotemporal and kinetic variables does not increase running-related injury risk in lower limbs | Malisoux et al. | 2024 | BMJ Open Sport & Exerc Med — [PMC10773390](https://pmc.ncbi.nlm.nih.gov/articles/PMC10773390/) | „Gait asymmetry was not associated with higher injury risk for investigated spatiotemporal and kinetic variables." (N=836, 6-Mo Follow-up, Kontaktzeit-SI Median 1.7 %) |
| Reference biomechanical parameters and natural asymmetry among runners across the age spectrum without a history of running-related injuries | Vincent et al. | 2025 | Frontiers in Sports and Active Living — [PMC12078198](https://pmc.ncbi.nlm.nih.gov/articles/PMC12078198/) | „Spatiotemporal asymmetries were generally low at < 4 % among all runners, irrespective of age." (N=250, 15–75 J) |
| Effects of running fatigue on lower extremity symmetry among amateur runners: From a biomechanical perspective | Gao et al. | 2022 | Frontiers in Physiology — [PMC9478459](https://pmc.ncbi.nlm.nih.gov/articles/PMC9478459/) | „running fatigue resulted in an increased asymmetry of load on the hip, knee and ankle joints"; Knie-/Hüft-Momenten-Asymmetrie +10–17 %. Stance-Time nicht primäres Outcome. (N=18) |
| Lower-Limb Biomechanical Adaptations to Exercise-Induced Fatigue During Running: A Systematic Review of Injury-Relevant Mechanical Changes | Anon. | 2026 | Life — [PMC12942261](https://pmc.ncbi.nlm.nih.gov/articles/PMC12942261/) | „few studies directly linked biomechanical changes to injury outcomes, necessitating cautious interpretation of injury relevance." |
| The Validity of a Three-Dimensional Motion Capture System and the Garmin Running Dynamics Pod in Connection with an Assessment of Ground Contact Time | Drobnič et al. | 2023 | Sensors 23(16):7155 — [PMC10459607](https://pmc.ncbi.nlm.nih.gov/articles/PMC10459607/) | „the Garmin Running Dynamics Pod significantly underestimated … the GCTs at low, medium, and fast step rates." Bias −81 bis −120 ms, LoA 72–111 ms. |
| Reproducibility and Validity of the Myotest for Measuring Step Frequency and Ground Contact Time in Recreational Runners | Roell et al. | 2015 | PLOS ONE — [PMC4415832](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4415832/) | Moderate GCT-Reliabilität bei 14 km/h, **schlecht** bei 10–12 km/h; signifikante Abweichung gegen Kraftplatten. |
| Ground Contact Time Balance Data (Instinct 2 Manual, exemplarisch für die Baureihe) | Garmin | — | Garmin — [Manual](https://www8.garmin.com/manuals/webhelp/GUID-31D23DBB-57C2-4DF7-A0C9-8D1A00AB4BE7/EN-US/GUID-B917540E-186D-4546-943F-4CD694B11BDC.html) | „If your data screen displays both numbers, for example 48–52, 48 % is the left foot and 52 % is the right foot." Populationszonen: „Good ≤ 50.7 %, Fair 50.8–52.2 %, Poor > 52.2 %". |
| RunningDynamicsData (Connect IQ API) — Feld-Definition `stance_time_balance` | Garmin | — | Garmin Developer — [API-Doc](https://developer.garmin.com/connect-iq/api-docs/Toybox/AntPlus/RunningDynamicsData.html) | „Filtered instantaneous stance time percentage (0 – 100 %, 0.25 % precision)." Seite (L/R) wird **nicht** explizit definiert. |
| What kind of value is left_right_balance? (FIT-SDK-Diskussion — Bike-Power-Kanal, **nicht** identisch mit `stance_time_balance`) | Garmin Forum / Ben FIT | — | [Forum-Thread](https://forums.garmin.com/developer/fit-sdk/f/discussion/372562/what-kind-of-value-is-left_right_balance) | Bit-Masking-Schema (MSB=Seite, 7 LSB=Wert) für `left_right_balance` — gilt **nicht** für den Single-Scalar `stance_time_balance`; damit ist die Seiten-Konvention für Running Dynamics offener. |
| Fatigue-Related Changes in Spatiotemporal Parameters, Joint Kinematics and Leg Stiffness in Expert Runners During a Middle-Distance Run | Apte et al. | 2021 | Frontiers in Sports and Active Living — [PMC7926175](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7926175/) | „expert runners change their stance time, rather than their step frequency or step length in order to maintain the constant running speed as long as possible" — Kontext für erwartete absolute GCT-Verlängerung unter Ermüdung. |
| Metabolic and biomechanical responses to running-related fatigue assessed with optimal control simulations tracking wearable sensor signals | Royal Society Open Science | 2026 | Royal Society Open Science 13(1):250668 — [Article](https://royalsocietypublishing.org/rsos/article/13/1/250668/478861/Metabolic-and-biomechanical-responses-to-running) | Trainierte Läufer: „preserving biomechanical stability and running efficiency despite increasing perceived fatigue" — Grundrausch-Drift bei Trainierten eher klein. |

## Application in framework

**Was ändert sich in den Coach-Regeln:**

- **`framework/agents/coach-analyst.md` + `framework/agents/planner.md`
  (Vorschlag zur Ergänzung, athlete-approval-pflichtig):** GCT-Balance
  ist in der Liste der Metriken, die **nicht** als eigenständiger
  Trainings-/Session-Finding gebrieft werden (analog zur bestehenden
  Regel für Stride-Pace-Zahlen und Cardiac-Startup-Drift). Ein
  beobachteter Balance-Drift kann als **deskriptive Zusatz-Information**
  im Aktivitäts-NOTE dokumentiert werden, ist aber **kein**
  Coach-Analyst-Growth-Area und **kein** Anlass, das Trainings-Design
  ohne symptomatische Bestätigung zu ändern.

- **`framework/research/README.md` Index-Zeile:** neu eintragen (2026-07-25).

- **`framework/CLAUDE.md` „Briefing rule — head coach does not seed
  measurement artifacts as findings":** eine vierte Ziffer für
  Running-Dynamics-Balance-/Asymmetrie-Zahlen wäre konsequent — die
  Metriken haben denselben Charakter wie Stride-Pace: sensor-noise-
  dominiert, ohne prospektive Coaching-Bedeutung; damit auch nicht als
  Finding zu handhaben.

- **Kein** Eintrag in `training_paradigms.md`, weil kein Trainings-Paradigma
  aus dieser Metrik ableitbar ist.

- **Athleten-individuelle Anwendung** (Baseline-Werte, individuelles
  Drift-Muster, Ergebnis der empirischen FIT-Feld-Verifikation für die
  konkrete Uhr/Firmware): gehört in `config/` (Wrapper), nicht hier.
  Die generische Logik („Baseline aus min 5–25, rollierender
  5-min-Median, 2 × SD als Auffälligkeits-Schwelle") ist hier
  dokumentiert und athleten-agnostisch.

## Open questions / Caveats

- **Belastbare Peer-Reviewed-Test-Retest-Daten spezifisch für den
  Balance-Kanal** (nicht die absolute GCT) in feld-relevanten
  Dauerlauf-Bedingungen fehlen. Bis dahin ist die Rausch-Untergrenze
  eine Schätzung aus der absoluten-GCT-Reliabilität.
- **Erwartungswert des „normalen" Ermüdungs-Drifts bei gesunden
  trainierten Läufern** über 60–120 min ist nicht publiziert. Ohne
  diese Kontrollgröße bleibt „ist mein Drift größer als der
  Populations-Drift?" empirisch offen — nur die athleten-individuelle
  Baseline über mehrere Läufe kann diese Lücke schließen.
- **Prognostischer Wert der fehlenden Post-Belastungs-Normalisierung**:
  keine prospektive Evidenz. Hypothesengenerierend, nicht validiert.
- **FIT-Feld-Konvention `stance_time_balance` über Firmware-Versionen**:
  die empirische Verifikation muss beim nächsten Firmware-Update
  ggf. wiederholt werden.
- **Sekundäre Metriken**, die die Face-Validity eines Balance-Drifts
  stützen würden — vertikale Oszillations-Asymmetrie, seitenspezifische
  vertikale Ratio, ggf. lauf-nachfolgende einbeinige RSI-Tests — sind
  in der Praxis erhebbar, aber ebenfalls schwach validiert. Ein
  konvergentes Muster über mehrere schwach validierte Kanäle ist
  aussagekräftiger als ein Einzelkanal-Trigger.
- **Interventionsseite:** selbst wenn ein Drift-Muster reproduzierbar
  wird, sagt die Metrik nichts darüber, **welche** Intervention hilft
  (einbeinige Kraft, Hüft-Abduktor-Aktivierung, Laufbahn-Camber-Rotation,
  Schuh-Wechsel). Das bleibt Physio-/Coach-Entscheidung auf Basis der
  gesamten Bewegungsanalyse.
