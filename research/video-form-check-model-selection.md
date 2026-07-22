# Video form check — model selection, sampling limits, and bias control

**Erstellt:** 2026-07-22

## TL;DR

1. **Die Modellwahl ist nicht der wichtigste Hebel — die Abtastung ist es.**
   Bei Default-Sampling (~1 fps) auf einem chat-komprimierten Clip beantwortete
   *dasselbe* Modell eine binäre Wahrnehmungsfrage („Füsse gestapelt oder
   gestaffelt?") über wiederholte identische Läufe **inkonsistent** — in einem
   lokalen Test 2 von 6 Läufen korrekt, also kaum über Zufallsniveau. Die
   Information ist in den abgetasteten Frames schlicht nicht belastbar
   enthalten. Kein Modellwechsel behebt das.
2. **Was ein neueres Modell sehr wohl verbessert: zu wissen, was es NICHT sieht.**
   Im selben Test antwortete die neuere Generation bei der Lendenwirbelsäule
   („durch Kleidung und Aufnahmewinkel nicht erkennbar") und beim
   ausserhalb des Bildes liegenden Schulterblatt („nicht im Bild") korrekt
   ablehnend — während die Vorgängergeneration zu beiden Punkten
   selbstbewusste Befunde produzierte. Das ist der eigentliche Gewinn.
3. **Herstellerbenchmarks ersetzen keinen Smoke-Test.** Ein Kandidat, der
   MotionBench anführt (72.4, herstellerselbstberichtet), fiel im lokalen
   Test mit einer falschen Wahrnehmungsantwort *bei hoher angegebener
   Sicherheit* durch und behauptete zusätzlich einen Ermüdungstrend, den das
   Material nicht hergibt. Vor Produktivschaltung eines Modells gehört ein
   Test gegen einen Clip mit **bekannter Ground Truth**.
4. **Sycophancy lässt sich nicht durch Nachfragen beheben.** Der VISE-Befund:
   Contradiction-Checking („bist du sicher?") *verschlechtert* das Verhalten.
   Wirksam ist struktureller Kontext-Entzug: Wahrnehmung und Bewertung in
   getrennte Calls, wobei der Wahrnehmungs-Call **keinen** Athleten-Kontext
   sieht.

## Ausgangsbefund

Ein realer Formcheck (Seitstütz mit Rotation, 47 s, über einen Chat-Kanal
transportiert, direkte Video-Analyse mit der damaligen Default-Generation)
produzierte drei unterschiedliche Fehlerklassen:

| # | Fehler | Klasse |
|---|--------|--------|
| 1 | Fussstellung als „gestapelt" gemeldet, tatsächlich gestaffelt | Perzeption |
| 2 | „Hüfte verliert über den Satzverlauf progressiv an Höhe" — Vergleich früher/später Top-Positionen widerlegt das | fehlender Zeitvergleich |
| 3 | Bestätigte eine Hohlkreuz-Tendenz, die dem Modell zuvor als Athleten-Kontext mitgegeben worden war, in einer vom Bild nicht gedeckten Deutlichkeit | Confirmation Bias |

Fehler 3 ist **prompt-induziert**, nicht modell-induziert: Der Athleten-Kontext
lag im selben Call wie das Video.

## Lokaler Smoke-Test (Ground Truth bekannt)

Gegen denselben Clip, Perzeptions-Prompt ohne Athleten-Kontext, mit
erzwungener „nicht erkennbar"-Option:

| Frage | Ground Truth | Neuere Pro-Generation | MotionBench-Spitzenreiter (Lite-Klasse) |
|---|---|---|---|
| Fussstellung | gestaffelt | **instabil** — 2/6 korrekt über wiederholte Läufe | falsch, „sicher" |
| Stützarm | rechts | korrekt | korrekt |
| Lendenwirbelsäule | aus diesem Winkel nicht beurteilbar | **korrekt abgelehnt** (Kleidung + Winkel als Grund genannt) | — |
| Schulterblatt der Stützseite | nicht im Bild | **korrekt abgelehnt** | — |
| Hüfthöhe früh vs. spät | kein belegbarer Trend | Trend behauptet | Trend behauptet, „ermüdungsbedingt" |

Interpretation: Die erzwungene Nichtwissen-Option wirkt — sie verwandelt zwei
frühere Fehlbefunde in korrekte Enthaltungen. Die Fussstellung bleibt trotzdem
unzuverlässig, weil die Frage an der Abtastung scheitert, nicht am Urteil. Die
Trendfrage bleibt ebenfalls unzuverlässig: Modelle zitieren die geforderten
Zeitstempel und behaupten den Trend trotzdem.

## Konsequenzen für die Praxis

### Abtastung und Aufnahme (der grösste Hebel)

- **Clip-Länge 20–40 s, 3–6 Wiederholungen.** Bei Default-1-fps ergibt ein
  47-s-Clip ~4–6 Frames pro Wiederholung; eine Top-Position ist dann oft von
  einem einzigen Frame repräsentiert, und ein Früh-Spät-Vergleich ist
  strukturell unmöglich.
- **Framerate explizit setzen:** 4–6 fps für Kraft-/Core-/Reha-Wiederholungen;
  **8–10 fps für Laufstil** (bei ~170 spm dauert ein Gangzyklus ~0.7 s).
- **Höchste verfügbare Medienauflösungs-Stufe wählen.** Bei Gemini gilt für
  Video ein Deckel von 70 Tokens/Frame bei `low` *und* `medium` — identisch —
  gegenüber 280 bei `high`. Erst mit `high` lohnt überhaupt eine höhere
  Quellauflösung.
- **Quellauflösung mindestens 720p**, Kamera fix (Stativ), ganzer Körper im
  Bild, senkrecht zur Beobachtungsebene, kein Zoom, kein Schwenk —
  Kamerabewegung ist eine eigene Fehlerquelle der Bewegungsinterpretation.
- **Kein Transport über Chat-Kanäle.** Die Rekodierung kostet genau die
  Detailtiefe, an der Perzeptionsfragen hängen.
- Kostenrahmen: ~30 s × 5 fps × 280 Tokens ≈ 42 000 Tokens — im Bereich weniger
  Cent pro Formcheck. Frames zu sparen wirft Genauigkeit weg, ohne nennenswert
  Kosten zu sparen.

### Prompting

- **Zwei getrennte Calls.** Call 1 (Wahrnehmung) sieht das Video und **keinerlei**
  Athleten-Kontext — keine Verletzungshistorie, keine Reha-Phase, keine
  Verdachtsdiagnose; Auftrag nur: „beschreibe, was sichtbar ist", mit Verbot von
  Wertungsvokabular. Call 2 (Bewertung) sieht **nur den Text aus Call 1**, nie
  das Video, und bekommt dort den Athleten-Kontext. Damit kann eine Hypothese
  die Wahrnehmung strukturell nicht mehr färben.
- **Nichtwissen erzwingen:** je Beobachtung `sicher | unsicher | nicht erkennbar`,
  und „nicht erkennbar" ausdrücklich als vollwertige, erwünschte Antwort
  deklarieren. Das ist die im Test wirksamste Einzelmassnahme.
- **Räumliche Relationen zerlegen** statt zusammenfassen: getrennt nach
  Bildkoordinaten (links/rechts), Tiefenrichtung (vorne/hinten), Kontaktpunkten
  und Verdeckung — statt einer Sammelfrage „wie stehen die Füsse".
- **Zeitstempelpflicht** für jede Beobachtung; Trendwörter (*progressiv*,
  *zunehmend*, *ermüdungsbedingt*) nur zulässig, wenn zwei Zeitstempel zitiert
  **und** die Differenz konkret benannt wird. Auch damit bleibt die Trendaussage
  schwach — im Zweifel als unbelegt behandeln.
- **Wiederholungszahl vorgeben, nicht abfragen.** Repetition Count ist auf
  MotionBench die schwächste Kategorie überhaupt.
- **Kein „bist du sicher?"-Nachfassen.** Verschlechtert das Verhalten messbar.

### Modellauswahl

- **Slugs pinnen.** `~`-präfigierte Alias-Routen re-pointen ohne Vorwarnung und
  ohne Rollback — für einen Check, der Progressions-Entscheidungen gatet, ist ein
  stillschweigender Modellwechsel ein Fehlerrisiko.
- **Benchmark-Führung ist kein Auswahlkriterium für sich**, insbesondere nicht
  bei herstellerselbstberichteten Zahlen. Gegen einen Clip mit bekannter Ground
  Truth testen.
- Benchmarks mit Bezug zur Aufgabe: **MotionBench** (feinkörnige
  Bewegungswahrnehmung, inkl. Repetition Count), **Video-MME-v2** (zeitliche
  Ordnung, Cross-Segment-Inferenz). Untertitel-gestützte VideoMME-Werte sind für
  stumme Formcheck-Clips ohne Aussagekraft.

## Offene Punkte

- Ob eine höhere Framerate plus `high`-Medienauflösung die Fussstellungs-Frage
  tatsächlich stabilisiert, ist **nicht verifiziert** — der Test lief auf dem
  vorhandenen chat-komprimierten Material. Mit dem ersten
  Originalauflösungs-Upload gegenprüfen.
- Der Zwei-Call-Aufbau ist als Empfehlung belegt, im Code aber noch nicht
  umgesetzt (Stand dieses Dokuments: Modell-Slugs und Transport-Guard sind
  umgesetzt).

## Quellen

| Quelle | Einordnung |
|---|---|
| [MotionBench (CVPR 2025)](https://motion-bench.github.io/) — feinkörnige Bewegungswahrnehmung, sechs Kategorien inkl. Repetition Count | hoch (akademisch), Leaderboard-Tabelle teils nur als Bild |
| [Video-MME-v2](https://arxiv.org/html/2604.05015v1) — zeitliche Ordnung, Cross-Segment-Inferenz | hoch (unabhängig) |
| [Flattery in Motion / VISE](https://arxiv.org/html/2506.07180v3) — Sycophancy in Video-LLMs; Contradiction-Checking verschlechtert, Key-Frame-Selection hilft | hoch für Mechanismen; getestete Modelle sind Vorgängergeneration, Rangfolge nicht übertragbar |
| [Point-light biological motion in MLLMs](https://arxiv.org/pdf/2509.23517) — Modelle stützen sich bei Bewegung stark auf Kontext-Priors statt auf Kinematik | hoch; begründet die Kontext-Trennung |
| [Gemini Media Resolution](https://ai.google.dev/gemini-api/docs/media-resolution) / [Video Understanding](https://ai.google.dev/gemini-api/docs/video-understanding) | hoch (offizielle API-Doku) — Token-/fps-/Auflösungsgrenzen |
| [OpenRouter: Latest-Resolution](https://openrouter.ai/docs/guides/routing/routers/latest-resolution), [Video](https://openrouter.ai/docs/features/multimodal/videos) | hoch (offizielle Doku) — Alias-Semantik, providerabhängige Video-Einschränkungen |
| Herstellerangaben zu MotionBench/VideoMME einzelner Modellfamilien | mittel (Selbstauskunft) — im lokalen Test nicht reproduziert |
| Lokaler Smoke-Test gegen Clip mit bekannter Ground Truth | hoch für die konkrete Aussage, klein (n=6 Läufe auf einem Clip) |
