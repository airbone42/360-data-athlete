# Video form check — model selection, sampling limits, and bias control

**Erstellt:** 2026-07-22

## TL;DR

0. **Die Fehlerklasse ist statisch-strukturell, nicht zeitlich — und daraus
   folgt der Zuschnitt der Pipeline.** Sämtliche real aufgetretenen
   Fehlbefunde betrafen Auflagepunkte, Seitigkeit, mitgeführtes Gerät oder die
   Kamerageometrie; kein einziger betraf Tempo oder Verlauf. Alle waren als
   `sicher` ausgewiesen, mehrere entstanden *nach* Einführung der
   Zwei-Call-Trennung. Konsequenz: Perzeption wird nach Aussagetyp getrennt.
   Struktur-Fragen gehen an **Standbilder**, Bewegungs-Fragen ans Video —
   siehe „Transport-Grenze" unten, dort steht die Zahl, die das erzwingt.
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

## Transport-Grenze (Korrektur, 2026-09-07)

Die ursprüngliche Kernempfehlung dieses Dokuments — Framerate explizit setzen
und die höchste Medienauflösungs-Stufe wählen — ist über den eingesetzten
Transportweg **nicht umsetzbar**. Sie stand hier als „noch nicht umgesetzt";
richtig ist „so nicht erreichbar".

- **OpenRouter exponiert weder `media_resolution` noch `video_metadata.fps`.**
  Der einzige Gemini-spezifische Passthrough ist `processing: agentic|static`.
- **Für Video sind `unspecified`, `low` und `medium` identisch 70 Tokens pro
  Frame**, nur `high` gibt 280. Der Default ist also bereits die gröbste Stufe
  — es gab nie eine billigere, die man versehentlich gewählt hätte.
- **Ein Standbild bekommt im selben Default 1120 Tokens** (`high` ebenfalls
  1120, `ultra_high` 2240).

Der Faktor 16 zwischen Video-Frame und Standbild ist grösser als der Faktor 4,
den `high` auf dem Videopfad gebracht hätte — und er ist über den bestehenden
Transportweg erreichbar. Das ist der Grund, warum die Struktur-Fragen an
Standbilder gehen und nicht der Anbieter gewechselt wurde.

**Was der Split nicht behebt:** Der Bewegungs-Pass läuft weiterhin bei 70
Tokens/Frame. Zeitliche Aussagen bleiben schwach — sie sind durch die
Zeitstempel-Pflicht und „kein Trend belegbar" abgesichert, nicht durch
Auflösung. Das ist vertretbar, solange die Fehlerklasse statisch bleibt.

**Aufgeschobene Option mit benanntem Auslöser:** Träte eine *zeitliche*
Fehlerklasse auf — eine Aussage über Tempo, Wiederholungsunterschied oder
Bodenkontaktzeit, die eine Frame-Prüfung widerlegt —, dann ist der richtige
Schritt der Wechsel auf die direkte Gemini-API mit `video_metadata.fps`. Keine
Zahl an Standbildern ersetzt Framerate. Der Preis wäre eine zusätzliche
Abhängigkeit, ein zusätzliches Credential und der Verlust der gepinnten
Slug-Auflösung (Rollback-Sicherheit) — deshalb erst bei diesem Auslöser.

## Konsequenzen für die Praxis

### Abtastung und Aufnahme (der grösste Hebel)

- **Clip-Länge 20–40 s, 3–6 Wiederholungen.** Bei Default-1-fps ergibt ein
  47-s-Clip ~4–6 Frames pro Wiederholung; eine Top-Position ist dann oft von
  einem einzigen Frame repräsentiert, und ein Früh-Spät-Vergleich ist
  strukturell unmöglich.
- **Struktur-Fragen an Standbilder stellen, nicht ans Video.** Auflagepunkte,
  Seitigkeit, Gerät und Kamerageometrie werden an wenigen Frames in
  Originalauflösung erhoben (1120 Tokens/Bild statt 70/Video-Frame). Eine
  höhere Quellauflösung lohnt sich erst auf diesem Pfad — auf dem Videopfad
  wird sie wegtokenisiert, unabhängig davon, wie scharf die Datei ist.
- **Framerate und Medienauflösung sind über OpenRouter nicht steuerbar**
  (siehe „Transport-Grenze"). Für Bewegungs-Fragen bleibt es daher bei der
  Default-Abtastung; die Absicherung dort ist die Zeitstempel-Pflicht, nicht
  die Auflösung.
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

- Ob der Standbild-Pfad die Fussstellungs-Frage tatsächlich stabilisiert, ist
  **nicht verifiziert**. Der ursprüngliche Test lief auf chat-komprimiertem
  Material; die Zahlenlage (Faktor 16 im Token-Budget) begründet die Erwartung,
  belegt sie aber nicht. Erster Gegentest: ein Clip mit bekannter Ground Truth
  zur Auflagepunkt-Frage. Erfolgskriterium ist **entweder** die korrekte
  Antwort **oder** eine ehrliche Enthaltung — eine falsche Antwort mit
  `sicher` ist der Fehlschlag.
- Ob die erzwungene Enumeration (feste Auswahlliste statt Fliesstext) über die
  erzwungene Nichtwissen-Option hinaus etwas beiträgt, ist nicht isoliert
  gemessen. Beide wurden zusammen eingeführt.

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
