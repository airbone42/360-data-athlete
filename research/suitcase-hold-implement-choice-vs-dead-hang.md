# Einarmiger Suitcase-Hold: Implement-Wahl, Rotationsstabilität und Abgrenzung zum Dead Hang

**Erstellt:** 2026-07-28

## TL;DR

1. **Das Balance-Problem der Langhantel-Suitcase ist keine Technik-Schwäche, sondern
   eine konstruktive Eigenschaft des Implements.** Ein mittig gegriffener langer
   Stab hat seinen Schwerpunkt *auf* Griffhöhe → **indifferentes Gleichgewicht** in
   der Kippachse, kein rückstellendes Moment. Kettlebell, Ladepin und
   Farmer-Griff haben den Schwerpunkt *unter* der Hand → **stabiles Gleichgewicht**,
   sie zentrieren sich selbst. Mittenmarkierung behebt den Platzierungsfehler,
   **nicht** die fehlende Rückstellung. Korrekte Lösung = Implement-Wechsel;
   günstigste korrekte Lösung = **Ladepin**.
2. **Ein rotationsinstabiles einarmiges Implement umgeht eine Handgelenks-Lastdecke
   nicht — es umgeht nur deren Maßeinheit.** Eine in kg definierte Decke begrenzt
   *keine* Momente. Jeder Griff-Versatz erzeugt ein dauerhaft zu haltendes
   Deviationsmoment (Größenordnung: 20-kg-Stange, 5 mm Versatz ≈ 1 N·m; 40 kg,
   20 mm ≈ 8 N·m), das exakt auf die Radial-/Ulnardeviatoren und den
   ulnokarpalen Komplex geht — die Kombination *kraftvoller Griff + Deviation +
   axiale Kompression + Drehmoment* ist das klinisch beschriebene Belastungsmuster
   für ECU-/TFCC-Beschwerden. **Bei aktiver Handgelenks-Lastdecke ist ein
   rotationsinstabiles Einarm-Implement daher kontraindiziert**, nicht „gleichwertig
   mit weniger kg".
3. **Der Suitcase-Hold sub-maximiert beide Zwecke gleichzeitig.** Griff: ein
   beidhändiger Dead Hang liefert **pro Hand ~50 % KG** und damit mehr als eine
   typische Einarm-Carry-Last (Praxis-Anker ~25 % KG/Hand). Rumpf: der statische
   Suitcase-Hold erreicht kontralateral **31,4 % MVIC EO** (Ellestad 2024) —
   Stabilisations-/Ausdauerband, unterhalb der 40-%- bzw. 70-%-MVIC-Schwellen für
   Kraftadaptation —, während die **Lateral-Plank-Familie 72–103 % MVC EO / 107–199 %
   IO** erreicht (Kinney/Barrios 2020) **ohne jede Griffbeteiligung**. Die Hand
   limitiert also, bevor der Rumpf einen *Kraft*-Reiz sieht.
4. **Empfehlung bei begrenzter Blockzeit: sauber trennen, nicht kombinieren.**
   Griff → Dead Hang (bzw. Ladepin-Hold, wenn die Schulter der Limiter ist);
   Anti-Lateralflexion → Lateral-Plank-Familie. Der Suitcase-**Carry** (gehend)
   bleibt als integrativer Transfer-Reiz sinnvoll, ist aber weder die beste
   Griff- noch die beste Anti-Lateralflexions-Quelle.
5. **Dead Hang deckt den Griff-Anteil weitgehend ab, die Anti-Lateralflexion
   prinzipiell nicht** — und diese Lücke ist **nicht** durch einarmige oder
   asymmetrische Hang-Varianten schließbar: ein Hang ist ein Zugsystem, der
   Körperschwerpunkt richtet sich unter dem Aufhängepunkt aus, es entsteht kein
   *anhaltendes* Frontalebenen-Moment am Rumpf. Was entsteht, ist Schulterlast.
6. **Diagnostische Regel (generisch):** frühes Versagen (< ⅓ der Zielzeit) bei
   *gesunkenem* Last×Zeit-Produkt und *gestiegener* Anstrengung = **Kontroll-Limiter**
   (Drehmoment/Stabilität), nicht Kapazitäts-Limiter (Griffausdauer). Griffausdauer
   versagt spät und metabolisch.

---

## Question / Trigger

Auslöser: coach-geflaggte Unsicherheit aus realer Anwendung. Ein einarmiger
Suitcase-Hold wird erstmals mit einer Langhantel statt einer Kettlebell ausgeführt,
weil die verfügbaren Kettlebell-Stufen ausgereizt sind. Es tritt ein
Handhabungsproblem auf, das die Übung dominiert: mehrfaches Nachgreifen bis zur
mittigen Lage, Wegkippen der Stange im Sekundenbereich nach Satzbeginn, gemeldete
Anstrengung deutlich über dem Zielkorridor — bei objektiv **geringerem**
Last×Zeit-Produkt als in der vorangegangenen Kettlebell-Session.

Sieben generische Teilfragen:

1. Ist der mittige Griff an einer langen Stange ein technisch lösbares Problem oder
   eine inhärente Schwäche der Variante? Welche Implement-Alternativen sind
   etabliert, bewertet nach Reproduzierbarkeit der Last, Störanfälligkeit und
   Anschaffungsaufwand?
2. Was trainiert der Suitcase-Hold tatsächlich — Griffkraft oder
   Anti-Lateralflexion? Limitiert die Hand, bevor der Rumpf einen Reiz sieht?
3. Deckt ein beidhändiger Dead Hang den Griff-Anteil ab? Was deckt er
   ausdrücklich nicht ab, und schließen einarmige/asymmetrische Hang-Varianten die
   Lücke?
4. Wie ist die Schulter-Randbedingung abzuwägen (Hang belastet die Schulter,
   Suitcase-Hold lässt sie passiv hängen), wenn ein aktives Zugmuster in einer
   Rehabilitationsphase noch nicht freigegeben ist?
5. Welche Progressionsachsen stehen bei Carry-Holds vs. Hangs realistisch zur
   Verfügung, und welche ist bei Griff-Isometrie am wirksamsten?
6. Wie sieht bei begrenzter Blockzeit die effizienteste Zuordnung aus — eine Übung
   für beides oder zwei spezifische Reize?
7. **Zusatzfrage:** Belastet die Kipp-/Rotationskomponente eines einarmigen
   Langhantel-Holds das Handgelenk (Radial-/Ulnarabduktion, Pronation unter
   Drehmoment) in relevantem Ausmaß — und ist ein solches Setup mit einer aktiven
   Handgelenks-Lastdecke aus einer Sehnen-Rehabilitation vereinbar?

---

## Findings

### 1. Das Balance-Problem: inhärent, nicht technisch lösbar

#### 1.1 Der mechanische Kern — indifferentes vs. stabiles Gleichgewicht

Die relevante Unterscheidung ist nicht „lang vs. kurz", sondern **wo der
Schwerpunkt relativ zur Hand sitzt**:

| Implement | Lage des Schwerpunkts | Gleichgewicht in der Kippachse | Verhalten |
|---|---|---|---|
| Kettlebell (Bügel) | **unter** der Hand | **stabil** | Pendel, rückstellendes Moment ∝ m·g·h·sinθ → zentriert sich selbst |
| Ladepin / Loading Pin | **unter** der Hand | **stabil** | wie Pendel; zusätzlich beliebig fein ladbar |
| Farmer-Griff (Last unter/um die Griffachse) | unter bis auf Griffhöhe | stabil bis indifferent | konstruktionsabhängig, meist selbstzentrierend |
| Kurzhantel | **auf** Griffhöhe | indifferent | kein Rückstellmoment, aber sehr kleiner Hebel und kleines Trägheitsmoment |
| Langhantel, mittig gegriffen | **auf** Griffhöhe | **indifferent** | jeder Versatz erzeugt ein Moment, das nicht von selbst verschwindet |
| Sandbag | wandernd | instabil | Schwerpunkt nicht reproduzierbar |
| Trap-/Hex-Bar einarmig an einem Griff | **weit neben** der Hand | **instabil** | konstantes großes Kippmoment; keine Lösung, sondern Verschärfung |

Ein mittig gegriffener Stab ist damit **die einzige der genannten Varianten ohne
Rückstellung**. Es gibt kein Fertigkeitsniveau, auf dem dieses Verhalten
verschwindet — es gibt nur ein Fertigkeitsniveau, auf dem der Fehler kleiner wird.
Das ist der entscheidende Unterschied zu einem Techniklernproblem.

#### 1.2 Größenordnungs-Herleitung (eigene Rechnung, keine Studie)

Erstordnungs-Starrkörperrechnung, Annahmen: homogene 20-kg-Stange, 2,2 m Länge,
Trägheitsmoment um die Griffachse I = m·L²/12 ≈ 8,1 kg·m²; Griff-Versatz d vom
Schwerpunkt; Moment M = m·g·d; Winkelbeschleunigung α = M/I; Zeit bis Kippwinkel θ
aus θ = ½αt². Ohne aktive Korrektur.

| Versatz d | Moment M | Zeit bis 10° | bis 30° | bis 45° |
|---|---|---|---|---|
| 1 mm | 0,20 N·m | 3,8 s | 6,6 s | 8,0 s |
| 2 mm | 0,39 N·m | 2,7 s | 4,6 s | 5,7 s |
| 5 mm | 0,98 N·m | 1,7 s | 2,9 s | 3,6 s |
| 10 mm | 1,96 N·m | 1,2 s | 2,1 s | 2,5 s |
| 2 mm, Stange + 2×5 kg an den Enden | 0,59 N·m | 3,0 s | 5,2 s | 6,4 s |

Drei Konsequenzen, die das gemeldete Muster vollständig erklären:

- **Die Fehlertoleranz liegt im Millimeterbereich.** Schon 1–2 mm Versatz führen
  innerhalb einer typischen Haltevorgabe (20–40 s) zum vollständigen Wegkippen.
  Ein Mensch kann die Massenmitte einer Stange taktil nicht auf 1–2 mm treffen;
  Rändelung, Hülsenspiel und Scheibensitz liefern zudem keine verlässliche
  optische Referenz.
- **Die Latenz bis zur Wahrnehmbarkeit liegt im Sekundenbereich.** Der Fehler ist
  beim Aufnehmen nicht spürbar und wird erst nach mehreren Sekunden sichtbar — genau
  das Muster „kippt erst nach einigen Sekunden weg", und genau der Grund für
  mehrfaches Nachgreifen: das Feedback kommt zu spät, um beim Greifen korrigiert zu
  werden.
- **Korrektur = dauerhaft gehaltenes Handgelenks-Deviationsmoment.** Wer den
  Versatz nicht eliminiert, muss M über die gesamte Haltezeit aktiv gegenhalten.
  Über eine Handauflagefläche von ~9 cm entspricht 1 N·m einem Kräftepaar von
  ~11 N an den Handkanten — absolut klein, aber **positionsgebunden, dauerhaft und
  am Handgelenk wirkend** statt als reine axiale Zuglast wie bei einem Pendel-Implement.

Diese Rechnung ist eine Herleitung, keine Messung. Sie ist als Größenordnung
robust (sie hängt nur von Masse, Länge und Versatz ab), aber sie ist nicht
publiziert und darf nicht als Studienbefund zitiert werden.

#### 1.3 Was die Ergonomie-Literatur dazu sagt

Das Prinzip ist in der Handwerkzeug-Ergonomie seit langem kodifiziert. CCOHS
formuliert es als Konstruktionsregel: *„It is also important that the centre of
gravity be aligned with the centre of the gripping hand."* und, als eigene Regel,
*„Select tools that do NOT require wrist flexion, extension or deviation."*
Frontlastige Werkzeuge — also Werkzeuge mit Schwerpunkt außerhalb der Greifhand —
werden ausdrücklich als zusätzlich handgelenks- und unterarmbelastend beschrieben.
Ein mittig gegriffener langer Stab ist der Grenzfall: der Schwerpunkt *soll* in der
Hand liegen, aber die Konstruktion erzwingt keine Ausrichtung, sie überlässt sie
dem Anwender.

Ergänzend: Seo & Armstrong 2008 zeigen, dass die tatsächlich auf ein zylindrisches
Handle wirkende Normalkraft im Mittel **2,3-fach** über der klassisch gemessenen
Griffkraft liegt und dass das Verhältnis Handle-Durchmesser zu Handlänge 57–71 %
der Varianz in Normalkraft und Kontaktfläche erklärt. Sobald zusätzlich ein
Drehmoment gehalten werden muss, steigt der Kopplungsbedarf weiter — die
Griff-Anforderung eines instabilen Implements ist damit **nicht** durch die
Hantel-Masse beschrieben.

#### 1.4 Bewertung der Lösungsoptionen

| Option | Reproduzierbarkeit der Last | Störanfälligkeit | Anschaffung | Urteil |
|---|---|---|---|---|
| **Ladepin (Loading Pin)** | sehr hoch (beliebige Scheiben-Mikroschritte) | sehr gering (Pendel, selbstzentrierend) | gering (günstig, DIY möglich) | **Erste Wahl** — löst Balance *und* Lastdecke gleichzeitig |
| Kettlebell | mittel (grobe Sprünge, Deckel bei verfügbaren Stufen) | sehr gering | mittel, pro Stufe | gut, aber genau die Progression, die im Auslöser endet |
| Farmer-Walk-Griffe | hoch (Scheibenschritte) | gering | mittel–hoch, sperrig | gut, wenn ohnehin vorhanden |
| Kurzhantel | mittel (feste Stufen) bzw. hoch (verstellbar) | gering (kleiner Hebel, kleines I → Fehler sofort spürbar und klein) | mittel | solide Alltagslösung |
| Kürzere Stange (Technikstange 1,2–1,5 m) | hoch | **mittel** — halbiert L, aber Gleichgewicht bleibt indifferent | mittel | Symptomlinderung, keine Lösung |
| Mittenmarkierung / Tape an der Langhantel | unverändert | **hoch** — reduziert nur den Startfehler, erzeugt kein Rückstellmoment | ~0 | Teilmaßnahme, keine Lösung |
| Sandbag | **niedrig** (Schwerpunkt wandert) | hoch | gering | für eine gecappte Struktur ungeeignet |
| Trap-/Hex-Bar einarmig | hoch | **sehr hoch** (Schwerpunkt weit neben der Hand) | hoch | ungeeignet |

**Abgrenzung, um einen Scheinwiderspruch zu vermeiden:** Der in
[grip-diameter-vs-load-progression.md](grip-diameter-vs-load-progression.md)
auf Rang 2 geführte **Langhantel-/Rackpin-Towel-Hold** ist von diesem Befund
**nicht** betroffen — er ist *bilateral* und die Stange liegt auf Rackpins bzw.
wird an beiden Seiten gegriffen. Es entsteht kein einseitiges Kippmoment um eine
einzelne Hand. Betroffen ist ausschließlich der **einarmige, mittige Griff** an
einer freien Stange.

Coach-Konsens deckt sich damit — Implement-Empfehlungen der Praxisliteratur
nennen durchgängig Kettlebell/Kurzhantel als Standard: *„You'll find kettlebells
are the most popular, as they are easier to walk with. Dumbbells and sandbags also
work great."* (Fitness Drum). Die Langhantel-Variante existiert, wird aber als
fortgeschrittene Variante mit erhöhtem Balance-Anspruch geführt, nicht als
Standard-Progressionsstufe.

**Antwort auf Teilfrage 1:** teilweise lösbar (Markierung reduziert den
Startfehler, eine kürzere Stange reduziert die Empfindlichkeit), aber die Ursache
ist konstruktiv und bleibt bestehen. Die saubere Lösung ist der Wechsel auf ein
Implement mit Schwerpunkt unter der Hand — der Ladepin ist dabei zugleich die
Antwort auf die Lastdecke, die den Wechsel überhaupt ausgelöst hat.

---

### 2. Was der Suitcase-Hold tatsächlich trainiert — zwei Zwecke, getrennt betrachtet

#### 2.1 Anti-Lateralflexion: der Reiz ist real, aber im Stabilisations-Band

Der belastbarste quantitative Anker ist Ellestad et al. 2024 (*Int J Exerc Sci*,
N = 18, bilaterale Oberflächen-EMG, Last einarmig ~25 kg vs. beidhändig ~51 kg,
Haltedauer = Gehzeit über 25 m + 5 s). **Statischer Suitcase-Hold, %MVIC:**

| Muskel | kontralateral | ipsilateral |
|---|---|---|
| Externer Obliquus | **31,4 ± 4,2** | 7,3 ± 1,4 |
| Longissimus | 21,6 ± 1,8 | 4,0 ± 0,4 |
| Multifidus | 12,8 ± 1,1 | 4,1 ± 0,5 |
| Rectus abdominis | 15,2 ± 1,6 | 5,7 ± 0,7 |

Zum Vergleich der **beidhändige Farmer-Hold bei doppelter Gesamtlast**: EO
6,4 / 6,9 %, Longissimus 4,5 / 5,6 % — also **praktisch kein lateraler Reiz trotz
doppeltem Gewicht**. Die Asymmetrie, nicht die Last, erzeugt den Reiz. Das deckt
sich mit McGill/McDermott/Fenwick 2009 und der NSCA-Aufarbeitung (Taylor & Reed
2020): *„carrying a load in one hand generates a greater spine load than if the
load were split between two hands"* — und zwar *„even though twice as much weight
was carried when both hands were loaded"*. Der Mechanismus ist bei McGill die
Frontalebenen-Stabilisierung durch Quadratus lumborum und laterale Bauchwand, die
*„stiffen the pelvis to prevent it from bending toward the side of the leg swing"*.

**Statisch vs. gehend:** Der Unterschied ist klein. Ellestad findet für den
gehenden Suitcase-Carry kontralateral EO 33,0 % vs. 31,4 % im Hold — der Hold
erfasst also praktisch den gesamten lateralen Reiz. Der gehende Carry addiert vor
allem die Schwungphasen-Komponente (Beckenkontrolle im Einbeinstand) und laut
NSCA-Aufarbeitung die Standbein-Glute-medius-/Vastus-lateralis-Beteiligung, die
bei kontralateraler Lastführung deutlich höher ist als bei ipsilateraler.

#### 2.2 Wo diese 31 % einzuordnen sind

Die im Framework bereits verankerten Adaptationsschwellen (siehe
[glute-hip-abductor-training-endurance-runner.md](glute-hip-abductor-training-endurance-runner.md)):
> 40 % MVIC als Untergrenze für Kraftzuwächse im aktiven Muskel (Reiman 2012),
> 70 % MVIC als robuste Kraft-Adaptationsschwelle (Boren 2011).

Ein Suitcase-Hold bei moderater Einarm-Last liegt mit ~31 % MVIC EO **unterhalb
beider Schwellen** — er ist ein **Stabilisations-/Kraftausdauer-Reiz**, kein
Kraftreiz für die laterale Bauchwand.

Die Gegenprobe liefert Kinney/Barrios et al. 2020 (*J Sport Rehabil*, N = 63),
die vier lateral zielende Isometrien direkt vergleichen:

| Aufgabe | Internus Obliquus | Externus Obliquus |
|---|---|---|
| Trunk-elevated side-unsupported | 199 % | **103 %** |
| Feet-elevated side-supported | 205 % | 55 % |
| **Lateral Plank (Side Plank)** | 107 % | **72 %** |
| Side-lying Hip Abduction | 48 % | 20 % |

Die Autoren empfehlen im Originaltext *„For independent exercise, we recommend the
lateral plank task, unless arm or shoulder pathologies are present, whereby the
feet-elevated side-supported task may be favorable."*

**Wichtiger Methodik-Caveat:** Die Werte > 100 % zeigen, dass die dort verwendete
MVC-Normalisierungsaufgabe das Maximum unterschätzt hat. Ein direkter
Zahlenvergleich mit Ellestads %MVIC ist deshalb **nicht** zulässig; die Aussage ist
**richtungsweisend**, nicht metrisch: die Seitstütz-Familie liegt eine
Größenordnung von Anforderung über einem moderat beladenen Suitcase-Hold, und zwar
**ohne jede Griffbeteiligung**.

#### 2.3 Limitiert die Hand, bevor der Rumpf einen Reiz sieht?

**Ja — für einen Kraftreiz. Nein — für einen Stabilisationsreiz.**

- Um den EO in Richtung 70 % MVIC zu bringen, wäre grob die doppelte Einarm-Last
  nötig. Bei einer Haltezeit im 20–40-s-Band liegt das an oder über der
  Support-Grip-Kapazität — die Hand gibt zuerst nach. Die Praxis-Literatur
  formuliert das direkt: *„You may discover it is your grip that is the limiting
  factor, instead of weak obliques"* (Fitness Drum).
- Umgekehrt gilt aber auch: bei einer Last, die *griffseitig* voll fordert, ist
  der Griff selbst noch nicht maximal gefordert im Vergleich zum Hang (siehe 3.1) —
  weil eine Einarm-Carry-Last typischerweise unter der Hang-Last pro Hand liegt.

**Der Suitcase-Hold sub-maximiert damit beide Zwecke gleichzeitig.** Das ist kein
Argument gegen die Übung — Stabilisationsreiz und Transfer ins Gehmuster sind
legitime Ziele — wohl aber ein Argument dagegen, ihn als *primäre* Quelle für
Griffkraft **oder** für Anti-Lateralflexions-Kraft zu führen.

---

### 3. Dead Hang als Alternative

#### 3.1 Griff-Anteil: weitgehend abgedeckt, teils übererfüllt

Ein beidhändiger Dead Hang am Körpergewicht liefert **pro Hand ~50 % Körpergewicht**
in reinem Support-Grip. Praxis-Referenz für Carry-Lasten sind ~25 % Körpergewicht
pro Hand (Fitness Drum: *„a weight that is ¼ of your total bodyweight"*), womit der
Hang pro Hand grob **das Doppelte** liefert. Der Modus ist derselbe
(Support-/Halte-Griff), und die Fingerflexoren sind die dominanten Agonisten:
Ferrer-Uris et al. 2023 (*PeerJ*, N = 25) zeigen für maximale isometrische
Dead-Hangs FDP und FDS als führende Muskeln, mit Griffpositions-abhängigen
Maximallasten von 133–190 % Körpergewicht — der Hang ist also nach oben weit offen.

**Was der beidhändige Hang ausdrücklich nicht abdeckt:**

| Lücke | Warum |
|---|---|
| **Anti-Lateralflexion** | siehe 3.2 — strukturell, nicht dosierungsbedingt |
| **Seitendifferenzierte Griff-Last** | beide Hände tragen gleichzeitig; eine schwächere Seite kann nicht gezielt höher belastet werden |
| **Griff-Modi Crush und Pinch** | Hang ist reiner Support-Grip (Modus-Systematik siehe [grip-training-progression.md](grip-training-progression.md)) |
| **Feine Einstiegs-Dosierung** | Untergrenze ist ~½ Körpergewicht pro Hand; darunter nur mit Fußunterstützung/Band, was die Last schlecht reproduzierbar macht |
| **Schulter-Neutralität** | siehe 4 — der Hang ist die schulterlastigste Griff-Variante |

#### 3.2 Warum einarmige/asymmetrische Hangs die Anti-Lateralflexions-Lücke nicht schließen

Der Grund ist systemisch, nicht dosierungsbedingt:

- Der **Suitcase-Hold ist ein Drucksystem mit Bodenbasis**: die Bodenreaktionskraft
  greift an den Füßen an, die Last hängt seitlich versetzt daneben → daraus folgt
  ein **anhaltendes Frontalebenen-Moment** auf Rumpf und Becken, das aktiv
  gegengehalten werden muss. Genau das ist der Anti-Lateralflexions-Reiz.
- Der **Hang ist ein Zugsystem mit einem Aufhängepunkt**: der Körperschwerpunkt
  pendelt sich unter dem Griffpunkt aus. Im Gleichgewicht ist das resultierende
  Frontalebenen-Moment am Rumpf **null**. Ein einarmiger Hang erzeugt lateral
  bestenfalls eine *transiente* Ausrichtungsarbeit, kein Haltemoment.
- Was der einarmige Hang stattdessen erzeugt: volle Körpergewichts-Traktion durch
  **ein** Glenohumeralgelenk plus Rotationskontrolle — d. h. die Kosten fallen fast
  vollständig in der Schulter an, nicht im lateralen Rumpf.

Die Lücke ließe sich nur durch ein **Zwei-Punkt-System** schließen (Füße fixiert
*und* Hand an der Stange), was mechanisch eine laterale Ketten-Isometrie ist und
damit ohnehin in die Seitstütz-Familie fällt — dann ist der Seitstütz die direktere
und billigere Übung.

**Antwort auf Teilfrage 3:** Griff ja (mit den genannten Lücken), Anti-Lateralflexion
strukturell nein, und die Lücke ist mit Hang-Varianten nicht schließbar — nur mit
einem zusätzlichen Schulterpreis, der den Zweck nicht erfüllt.

---

### 4. Schulter-Randbedingung — und die Handgelenks-Randbedingung dagegen

#### 4.1 Der Hang ist die schulterlastigste Griff-Variante

Das ist im Framework bereits belegt und dosierungsrelevant kodifiziert
([grip-isometry-vs-scapular-stabilization-same-day.md](grip-isometry-vs-scapular-stabilization-same-day.md)):
bodennahe Griff-Isometrie mit adduziertem Arm (**Klasse A**: Farmer-/Suitcase-Hold,
Pinch, Ladepin) koppelt praktisch nicht auf die Rotatorenmanschette und unterliegt
nur den griff-eigenen Limits; der **Dead Hang (Klasse B)** kombiniert maximale
Humeruselevation, volle Körpergewichts-Traktion und — als *Active Hang* — Lower
Trap/Serratus als Trainingsinhalt und **zählt daher ins Schulter-Budget**.

Die klinische Literatur ist in dieselbe Richtung eindeutig: der Hang bringt große
Kraft durch ein relativ instabiles Gelenk am Ende seines Bewegungsumfangs; bei
Labrum-/Manschettenpathologie, Hypermobilität oder Instabilität ist er unklug
(vgl. auch die Indikations-Matrix in
[passive-vs-active-hang.md](passive-vs-active-hang.md)).

**Abwägungsregel, generisch formuliert:** Solange ein aktives Zugmuster in einer
Schulter-Rehabilitationsphase nicht freigegeben ist, ist der Hang **kein**
freigegebener Ersatz für einen bodennahen Griff-Hold, sondern eine Übung aus einer
gate-pflichtigen Klasse. Die Reihenfolge ist dann nicht „Hang statt Hold", sondern
**Hold jetzt, Hang nach Freigabe** — und der Griff-Progressionspfad läuft
zwischenzeitlich über ein bodennahes Implement mit freier Last-Achse (Ladepin).
Kinney/Barrios 2020 liefern hierfür sogar die passende Anti-Lateralflexions-Variante:
bei Arm-/Schulterpathologie ausdrücklich **feet-elevated side-supported** statt
Lateral Plank.

#### 4.2 Die Gegenrichtung: Handgelenk

Hier kehrt sich die Rangfolge um. Der Hang lädt das Handgelenk in **nahezu neutraler
Stellung unter axialem Zug**, ohne Deviationsmoment und ohne Drehmoment. Der
Suitcase-Hold mit *rotationsstabilem* Implement ebenfalls (axiale Zuglast, Hand
neutral). Der Suitcase-Hold mit *rotationsinstabilem* Implement dagegen erzeugt
genau das, was der Hang nicht erzeugt.

**Daraus folgt eine Zwei-Constraint-Matrix:**

| aktive Einschränkung | geeignete Griff-Quelle |
|---|---|
| Schulter gecappt, Handgelenk frei | bodennaher Hold (Klasse A), Implement egal, solange handhabbar |
| Handgelenk gecappt, Schulter frei | Dead Hang (neutrales Handgelenk, axialer Zug) |
| **beide gecappt** | **bodennaher Hold mit rotationsstabilem Implement** (Ladepin/KB) — Schulter passiv an der Seite, Handgelenk neutral, Last frei fein dosierbar |
| keine Einschränkung | Hang für Griff-Progression (höhere Last, offene Last-Achse), Hold als Ergänzung |

---

### 5. Zusatzfrage: Drehmoment am Handgelenk und Vereinbarkeit mit einer Lastdecke

#### 5.1 Belastet die Kippkomponente das Handgelenk relevant?

Ja — und die vorhandene Griff-Literatur adressiert das systematisch nicht, weil sie
in **Kraft** (kg, %MVC) und **Geometrie** (Griffdurchmesser) denkt, nicht in
**Momenten**. Drei unabhängige Belege plus die Herleitung aus 1.2:

1. **Größenordnung des Moments.** 20-kg-Stange, 5 mm Versatz ≈ 1 N·m; 10 mm ≈ 2 N·m;
   eine mit Scheiben beladene Stange bei 20 mm Versatz erreicht ~8 N·m. Das ist
   ein dauerhaft zu haltendes Deviationsmoment, das in einer kg-basierten Lastdecke
   nirgends auftaucht.
2. **Deviation kostet Griffkraft — messbar.** O'Driscoll et al. 1992 (*J Hand Surg
   Am*, N = 20): die selbstgewählte Optimalstellung ist 35° Extension / 7°
   Ulnardeviation, und *„Grip strength was significantly less in any position of
   deviation from this self-selected position, even after accounting for fatigue"*;
   schon bei nur 15° Extension oder neutraler Radio-Ulnar-Stellung sinkt die
   Griffkraft *„to two thirds to three fourths of normal"*. Lamoreaux & Hoffer 1995
   (*Clin Orthop Relat Res* 314:152-155, N = 12) bestätigen den Deviationseffekt auf
   die Griffkraft mit p < 0,0001. **Ein kippendes Implement zwingt das Handgelenk aus
   der Optimalstellung und senkt damit die verfügbare Griffkraft, während es
   gleichzeitig zusätzliche Stabilisationsarbeit verlangt.**
3. **Klinisches Belastungsmuster.** Für ulnarseitige Handgelenksstrukturen ist die
   Kombination aus kraftvollem Griff, Ulnardeviation, axialer Kompression und
   Drehmoment das explizit beschriebene Provokationsmuster: der TFCC puffert das
   Handgelenk unter axialer Last und Ulnardeviation, Beschwerden werden verstärkt
   durch *„ulnar deviation of the wrist, twisting maneuvers, power grip, and axial
   compression or weight-bearing"* (StatPearls). ECU-Tendinopathie ist ihrerseits
   mit repetitiver Bewegung und axialer Belastung durch Handgelenk und Unterarm
   assoziiert (Zarro et al. 2024, *Hand (N Y)*, Review zu konservativen Optionen).
   Die arbeitsmedizinische Literatur ordnet die **Kombination** aus kraftvollem
   Greifen und ungünstiger Handgelenksstellung als Risikofaktor für
   Hand-/Handgelenks-Tendinitiden ein.

#### 5.2 Vereinbarkeit mit einer aktiven Handgelenks-Lastdecke

**Nein, ein rotationsinstabiles Einarm-Implement ist damit nicht vereinbar** — und
zwar aus einem präziseren Grund als „ist schwerer":

> Eine in Kilogramm formulierte Lastdecke begrenzt eine **Kraft**. Die
> Rotationsinstabilität erzeugt ein **Moment**. Das Moment skaliert mit
> Masse × Griff-Versatz und ist bei gleicher Masse praktisch unbegrenzt variabel.
> Die Decke misst damit nicht, was tatsächlich auf die gecappte Struktur wirkt.

Das ist die Antwort auf die eigentliche Frage: das instabile Implement **umgeht die
gecappte Struktur nicht** — es belastet sie über einen **anderen Vektor** neu, den
die Decke nicht erfasst. Die konservative Konsequenz ist nicht „weniger kg", sondern
**Implement-Wechsel auf ein rotationsstabiles Gerät**, damit die Decke wieder das
begrenzt, was sie zu begrenzen vorgibt. Danach ist die Last-Achse innerhalb der
Decke wieder regulär progressionsfähig (Anti-Stall-Logik in
[rpe-gate-validity-isometric-holds.md](rpe-gate-validity-isometric-holds.md)).

#### 5.3 Diagnostische Regel: Kontroll-Limiter vs. Kapazitäts-Limiter

Aus der Kombination der Befunde folgt ein generisch verwendbares Feld-Kriterium:

| Beobachtung | Griffausdauer-Limiter (Kapazität) | Drehmoment-/Kontroll-Limiter |
|---|---|---|
| Zeitpunkt des Versagens | **spät** im Satz, nahe der Zielzeit | **früh**, oft < ⅓ der Zielzeit |
| Qualität | lokales Brennen, langsames Aufgehen der Finger | plötzlicher Kontrollverlust, Implement kippt/dreht |
| Verhalten bei kleinerer Last | Zeit steigt systematisch | Problem bleibt (Versatz-abhängig, nicht last-abhängig) |
| Anstrengung vs. Last×Zeit | konsistent | **Anstrengung steigt, obwohl Last×Zeit sinkt** |
| Vorlauf | Satz startet sauber | mehrfaches Nachgreifen vor Satzbeginn |

Die dritte und vierte Zeile sind die belastbaren Diskriminatoren. Eine
Isometrie-Haltezeit ist nach Rohmert eine nichtlineare Funktion allein des %MVC
(Anker: [rpe-gate-validity-isometric-holds.md](rpe-gate-validity-isometric-holds.md));
ein Abbruch bei einem Bruchteil der Zielzeit *bei gesunkenem* Last×Zeit-Produkt ist
mit einer metabolischen Griff-Erschöpfung nicht vereinbar. Zusammen mit O'Driscoll
(Deviation senkt die verfügbare Griffkraft) erklärt das auch die
**Anstrengungs-Inflation ohne Last-Zuwachs** vollständig: mehr Stabilisationsarbeit
bei gleichzeitig reduzierter verfügbarer Griffkapazität.

**Wichtig für die Interpretation:** In diesem Muster ist der erhöhte
Anstrengungswert **kein** Progressions-Signal und **kein** Überlastungs-Signal der
Zielstruktur — er ist ein **Handhabungs-Artefakt**. Die Session ist als
Progressions-Datenpunkt für die Zielqualität nicht verwertbar; der Anker der
vorangegangenen sauberen Session bleibt gültig (Anti-Silent-Conservatism-Logik).

---

### 6. Progressionsachsen im Vergleich

| Achse | Carry/Hold (bodennah) | Hang | Bewertung für Griff-Isometrie |
|---|---|---|---|
| **Last** | verfügbar, aber **griff-gedeckelt**; mit Ladepin in Mikroschritten | verfügbar und **nach oben offen** (Gürtel/Weste); Untergrenze aber ~½ KG/Hand | **wirksamste Achse** — Sehnenadaptation ist intensitätsgetrieben (SMD 0,90 bei > 70 % MVC, Anker [tendon-reload-after-substitute-block.md](tendon-reload-after-substitute-block.md)) |
| **Haltezeit / TUT** | 20–40 s → 60–90 s Bänder | dito | zweite Achse, belegt, aber langsamer wirksam |
| **Griffdurchmesser** | frei wählbar (Handle/Handtuch) | frei wählbar (Stangendurchmesser, Handtuch, Seil) | **Spezifitäts-Achse, kein kg-Äquivalent** — Anker [grip-diameter-vs-load-progression.md](grip-diameter-vs-load-progression.md) |
| **Uni-/bilateral** | nativ unilateral | ein-/beidhändig, aber einarmig = Schulter-Achse | für Seitendifferenz nur der Hold brauchbar |
| **Dichte/Frequenz** | ≥ 48 h Spacing, ≤ 3 Sätze | dito | vollwertige Parallelachse (Anker rpe-gate-Doku) |
| **Implement-Stabilität** | technisch verfügbar | kaum | **keine legitime Progressionsachse** bei gecappter Struktur (siehe 5.2); ohne Cap allenfalls Variations-Reiz |
| **Statisch → gehend** | verfügbar | — | erhöht den Rumpf-/Gang-Anteil, nicht den Griff-Anteil |

Zwei strukturelle Schlüsse:

- **Für den Zweck Griffkraft ist der Hang die besser progressionsfähige Übung**
  (höhere Grundlast, freie Last-Achse ohne Balance-Nebenbedingung) — sofern die
  Schulter das zulässt.
- **Für den Zweck Anti-Lateralflexion ist die Carry-Achse griff-gedeckelt**, die
  Seitstütz-Familie dagegen nicht (Hebel, Fußerhöhung, Zusatzlast, unsupported
  Varianten sind alle griff-frei). Auch hier gewinnt die spezifische Übung.

Für alle Achsen gilt weiterhin die Gate-Architektur aus
[rpe-gate-validity-isometric-holds.md](rpe-gate-validity-isometric-holds.md):
Progression über ein **Leistungs-Gate** auf der Haltezeit bei fixer Last, RPE als
Log-Feld, nicht als Gate — und **eine Variable pro Session**. Ein
Implement-Wechsel ist selbst eine Variablen-Änderung: die Rückkehr-Session nach dem
Wechsel führt keine zusätzliche Progression mit.

---

### 7. Praktische Empfehlung bei begrenzter Blockzeit

**Trennen, nicht kombinieren.** Begründung in einem Satz: die beiden Zwecke
skalieren auseinander — der Rumpf braucht Asymmetrie (und relativ wenig Last),
der Griff braucht Last (und keine Asymmetrie), und die gemeinsame Übung deckelt
den Griff durch die Balance-Nebenbedingung und den Rumpf durch die Griffkapazität.

Vorschlags-Zuordnung, absteigend nach Ertrag pro Blockminute:

1. **Griff-Isometrie** — Dead Hang, wenn die Schulter frei ist; sonst bodennaher
   Hold mit **rotationsstabilem** Implement (Ladepin > Kettlebell > Farmer-Griff >
   Kurzhantel). Volumen-Caps unverändert: ≤ 1 Unterarm-Übung/Session, ≤ 3 Sätze,
   ≥ 48 h Spacing ([ninja-set-volume-tolerance.md](ninja-set-volume-tolerance.md)).
2. **Anti-Lateralflexion** — Lateral Plank als Standard; bei Arm-/Schulter-Pathologie
   die feet-elevated side-supported Variante (Kinney/Barrios 2020). Progression über
   Hebel/Erhöhung/Zusatzlast, griff-frei.
3. **Suitcase-Carry (gehend)** — als integrativer Transfer-Reiz, wenn Zeit übrig
   ist. Praxis-Dosierung: 2–4 Runden à 10–20 s mit fordernder Last (Taylor & Reed
   2020) bzw. ~¼ Körpergewicht pro Hand über eine Gehstrecke. **Nicht** als primäre
   Quelle für Griff- oder Rumpfkraft geführt.

Wenn nur **ein** Slot verfügbar ist: die Übung wählen, die auf die *aktuell
schwächere* Qualität zielt — und nicht die Kombiübung, weil sie beides
sub-maximiert. Wenn Griff und Rumpf beide offen sind und der Slot kurz ist, ist die
Seitstütz-Familie die zeit-effizientere Wahl (höchste Aktivierung pro Minute, kein
Equipment, keine Handhabungs-Varianz), und der Griff wandert in einen anderen Slot
mit ≥ 48 h Abstand.

---

### 8. Evidenzlage — explizit

Was **studienbelegt** ist: die EMG-Profile von Suitcase-Hold/-Carry vs.
Farmer-Hold/-Carry vs. Plank (Ellestad 2024); die Rangfolge lateral zielender
Isometrien (Kinney/Barrios 2020); die Rumpf-Anforderung asymmetrischen Tragens und
der Mechanismus über QL/laterale Bauchwand (McGill 2009); der Effekt von
Handgelenks-Deviation auf die Griffkraft (O'Driscoll 1992, Lamoreaux & Hoffer 1995);
die Griff-/Normalkraft-Beziehungen an zylindrischen Handles (Seo & Armstrong 2008);
die Muskel-Hierarchie und Lastbereiche im Dead Hang (Ferrer-Uris 2023); das
klinische Provokationsmuster ulnarseitiger Handgelenksstrukturen (StatPearls,
Zarro 2024).

Was **nicht** studienbelegt ist und hier als Herleitung gekennzeichnet bleibt:

- die Kipp-Zeitkonstanten-Tabelle (1.2) — eigene Starrkörperrechnung;
- der Vergleich „Suitcase-Hold vs. Seitstütz" als Zahlenvergleich — durch
  unterschiedliche MVC-Normalisierung nur richtungsweisend;
- die Diagnose-Tabelle Kontroll- vs. Kapazitäts-Limiter (5.3) — abgeleitet aus
  Rohmert-Logik + O'Driscoll, nicht als Diagnostikum validiert;
- die Implement-Rangfolge (1.4) — Kriterien-basierte Bewertung plus Coach-Konsens,
  kein Head-to-Head-Vergleich.

Es existiert **keine** Studie, die Suitcase-Hold und Dead Hang direkt gegeneinander
auf Griffkraft- oder Rumpf-Outcomes testet, und **keine** Studie zur
Rotationsstabilität von Trainings-Implements. Wo diese Arbeit über die Evidenz
hinausgeht, tut sie es über Trainingslehre und Biomechanik — die Empfehlungen aus
6 und 7 sind begründete Praxis-Ableitungen, keine Studienergebnisse.

---

## Primary sources

| Autor / Jahr | Titel | Journal / Link | Kernzitat |
|---|---|---|---|
| Ellestad SH, Holcomb TP, Swiergol AM, Holmstrup ME, Dicus JR — 2024 | The Quantification of Muscle Activation During the Loaded Carry Movement Pattern | Int J Exerc Sci 17(1):480-490 — [PMC11042841](https://pmc.ncbi.nlm.nih.gov/articles/PMC11042841/) | „The lateral abdominal wall muscles, like the EO, stiffen the pelvis in order to prevent side bending during the stepping process" — Suitcase-Hold kontralateral EO 31,4 ± 4,2 %MVIC vs. Farmer-Hold 6,4 %; Suitcase-Carry 33,0 % |
| McGill SM, McDermott A, Fenwick CMJ — 2009 | Comparison of different strongman events: trunk muscle activation and lumbar spine motion, load, and stiffness | J Strength Cond Res 23(4):1148-61 — [PubMed 19528856](https://pubmed.ncbi.nlm.nih.gov/19528856/) | „loaded carrying would enhance traditional lifting-based strength programs"; Muskeln wie der Quadratus lumborum erzeugen Frontalebenen-Torque zur Rumpf-/Beckenstabilisierung |
| Taylor J, Reed M — 2020 | Increase Hip and Trunk Stability with Loaded Carries for Injury Prevention, Rehabilitation, and Performance | NSCA Coach 7(3) — [nsca.com](https://www.nsca.com/education/articles/nsca-coach/increase-hip-and-trunk-stability-with-loaded-carries/) | „carrying a load in one hand generates a greater spine load than if the load were split between two hands" … „even though twice as much weight was carried when both hands were loaded"; Dosierung „2–4 rounds for 10–20 s with a weight that is challenging" |
| Kinney AL, Giel M, Harre B, Heffner K, McCullough T, Savino M, Scott A, Barrios JA — 2020 | Surface Electromyography of the Internal and External Oblique Muscles During Isometric Tasks Targeting the Lateral Trunk | J Sport Rehabil 30(2):255-260 — [PubMed 32369764](https://pubmed.ncbi.nlm.nih.gov/32369764/) | „The lateral plank task successfully activated the internal (107%) and external (72%) obliques" … „For independent exercise, we recommend the lateral plank task, unless arm or shoulder pathologies are present, whereby the feet-elevated side-supported task may be favorable." |
| O'Driscoll SW, Horii E, Ness R, Cahalan TD, Richards RR, An KN — 1992 | The relationship between wrist position, grasp size, and grip strength | J Hand Surg Am 17(1):169-177 — [PubMed 1538102](https://pubmed.ncbi.nlm.nih.gov/1538102/) | „Grip strength was significantly less in any position of deviation from this self-selected position, even after accounting for fatigue. With the wrist in only 15 degrees of extension or in neutral radio-ulnar deviation, grip strength was reduced to two thirds to three fourths of normal." |
| Lamoreaux L, Hoffer MM — 1995 | The Effect of Wrist Deviation on Grip and Pinch Strength | Clin Orthop Relat Res 314:152-155 — [journals.lww.com](https://journals.lww.com/clinorthop/Abstract/1995/05000/The_Effect_of_Wrist_Deviation_on_Grip_and_Pinch.19.aspx) | „A highly significant effect of wrist deviation on grip strength was found (p < 0.0001)" (N = 12; max. Ulnardeviation Ø 41°, Radialdeviation Ø 26°) |
| Seo NJ, Armstrong TJ — 2008 | Investigation of grip force, normal force, contact area, hand size, and handle size for cylindrical handles | Human Factors 50(5):734-744 — [PubMed 19110833](https://pubmed.ncbi.nlm.nih.gov/19110833/) | „Average total normal force on cylinders was 2.3 times greater than grip force measured using a split cylinder (R2 = 65%), regardless of the handle diameter examined." |
| CCOHS (Canadian Centre for Occupational Health and Safety) | Hand Tool Ergonomics — Tool Design | [ccohs.ca](https://www.ccohs.ca/oshanswers/ergonomics/handtools/tooldesign.html) | „It is also important that the centre of gravity be aligned with the centre of the gripping hand." / „Select tools that do NOT require wrist flexion, extension or deviation." |
| Ferrer-Uris B et al. — 2023 | Exploring forearm muscle coordination and training applications of various grip positions during maximal isometric finger dead-hangs in rock climbers | PeerJ — [PMC10249616](https://pmc.ncbi.nlm.nih.gov/articles/PMC10249616/) | N = 25; FDP/FDS als führende Agonisten; maximale Dead-Hang-Lasten 132,6–189,5 % Körpergewicht je Griffposition |
| StatPearls (NCBI Bookshelf) | Triangular Fibrocartilage Complex | [NBK537055](https://www.ncbi.nlm.nih.gov/books/NBK537055/) | Symptome verstärkt durch „ulnar deviation of the wrist, twisting maneuvers, power grip, and axial compression or weight-bearing"; TFCC puffert das Handgelenk unter axialer Last und Ulnardeviation |
| Zarro M, Goel R, Bickhart N, May CC, Abzug JM — 2024 | Extensor Carpi Ulnaris Tendinopathy in Athletes: A Review of the Conservative and Rehabilitative Options | Hand (N Y) — [journals.sagepub.com](https://journals.sagepub.com/doi/abs/10.1177/15589447221127331) | ECU-Tendinopathie assoziiert mit repetitiver Bewegung und axialer Belastung durch Handgelenk und Unterarm; Management über Load-Management, Aktivitätsmodifikation, progressives Krafttraining |
| Fitness Drum (Coach-Quelle) | Suitcase Carry Exercise — Benefits, Muscles Worked & Common Mistakes | [fitnessdrum.com](https://fitnessdrum.com/suitcase-carry/) | „You may discover it is your grip that is the limiting factor, instead of weak obliques" / „You'll find kettlebells are the most popular, as they are easier to walk with. Dumbbells and sandbags also work great." / Einstieg „a weight that is ¼ of your total bodyweight" |

**Quellen-Status:** Zeilen 1–10 sind peer-reviewed bzw. institutionelle
Referenzwerke. Die letzte Zeile ist eine Coach-Quelle und ausschließlich für
Praxis-Konventionen (Implement-Präferenz, Einstiegslast) zitiert — nicht als
evidenzgleichwertiger Beleg.

---

## Application in framework

Vorschläge — **nicht angewendet**, Umsetzung über Head-Coach/Athleten-Freigabe.

### Framework (generisch)

1. **`framework/agents/specialist-complementary.md` und
   `framework/agents/specialist-ninja.md`** — neue Implement-Wahl-Regel für
   einarmige Carries/Holds:
   - Einarmige Halte-/Trageübungen werden mit einem **rotationsstabilen** Implement
     verordnet (Schwerpunkt unter der Hand: Ladepin, Kettlebell, Farmer-Griff;
     Kurzhantel als praktikable Näherung). Eine **mittig gegriffene Langhantel ist
     kein zulässiger Ersatz**, wenn die Kettlebell-Stufen ausgereizt sind — die
     Standard-Eskalation ist der **Ladepin** (deckt sich mit der Rangfolge in
     `grip-diameter-vs-load-progression.md`).
   - Ein Suitcase-Hold/-Carry wird **nicht** als primärer Anti-Lateralflexions-
     *Kraft*reiz und **nicht** als primärer Griffkraft-Reiz geführt; er ist
     Stabilisations-/Transfer-Reiz.
   - Bei aktiver Handgelenks-Lastdecke: rotationsinstabile Einarm-Implements sind
     gesperrt — die Sperre ist **vektor-**, nicht kg-basiert.
2. **`framework/agents/specialist-complementary.md`** — Diagnose-Regel aus 5.3
   aufnehmen: frühes Versagen + gesunkenes Last×Zeit + gestiegene Anstrengung =
   Handhabungs-Artefakt → Session ist **kein** Progressions-Datenpunkt, der Anker
   der letzten sauberen Session bleibt stehen.
3. **`framework/scripts/validate_plan.py`** — neue mechanische Regel (WARNING),
   z. B. `check_unstable_unilateral_implement`: Beschreibung enthält ein
   Einarm-Carry/Hold-Muster (`suitcase`, `einarmig … hold/carry`) **und** ein
   Langhantel-/Barbell-/Sandbag-Token → Warnung mit Verweis auf dieses Dokument;
   ERROR, wenn zusätzlich eine aktive Handgelenks-Restriktion in
   `injury_locks.json` greift.
4. **`framework/research/grip-diameter-vs-load-progression.md`** und
   **`framework/research/rpe-gate-validity-isometric-holds.md`** — je eine
   „Siehe auch"-Zeile auf dieses Dokument (Rotationsstabilität als bislang
   fehlende Implement-Dimension bzw. Kontroll- vs. Kapazitäts-Limiter als
   Vorschaltprüfung vor jeder Gate-Entscheidung).
5. **`framework/config.example/`** — keine Änderung nötig; die Regel ist
   agent-seitig, nicht config-seitig, und Demo-Configs bleiben restriktionsfrei.

### Wrapper (`config/`, athlet-spezifisch — nur Vorschlag)

1. **`config/exercise_progressions.md`** — Implement des betroffenen
   Suitcase-Hold-Eintrags auf ein rotationsstabiles Gerät umstellen, Last-Anker der
   letzten sauberen Session beibehalten (kein prophylaktischer Deload), Langhantel-
   Variante als Ausführungsform streichen (nicht annotieren — Config-Hygiene).
2. **`config/equipment.md`** — Ladepin als Beschaffungs-/Bestandsposten aufnehmen;
   er löst gleichzeitig die Lastdecke *und* das Balance-Problem und ist die
   günstigste der geprüften Optionen.
3. **`config/athlete_static.md`** — bei aktiver Handgelenks-Lastdecke ergänzen,
   dass die Decke zusätzlich **rotationsinstabile Einarm-Implements** ausschließt
   (Begründung: kg-Decke begrenzt keine Momente).
4. **Struktur-Vorschlag** — Anti-Lateralflexion als eigenen, griff-freien Reiz aus
   der Seitstütz-Familie führen, statt sie im Griff-Block mitlaufen zu lassen;
   damit wird auch der Griff-Block wieder auf der Last-Achse progressionsfähig.

---

## Open questions / Caveats

1. **Kein Head-to-Head.** Es gibt keine Trainingsstudie „Suitcase-Hold vs. Dead Hang"
   auf Griffkraft-Outcome und keine auf Anti-Lateralflexions-Outcome. Die
   Trennungsempfehlung ist aus Aktivierungs- und Lastprofilen abgeleitet, nicht
   längsschnittlich getestet.
2. **Normalisierungs-Inkompatibilität.** Ellestad (%MVIC ≤ 100) und Kinney/Barrios
   (%MVC teils > 200) sind nicht direkt vergleichbar. Die Aussage „Seitstütz fordert
   die laterale Bauchwand deutlich stärker als ein moderat beladener Suitcase-Hold"
   ist robust in der Richtung, nicht in der Zahl.
3. **QL nicht direkt gemessen.** Ellestad misst RA, EO, Longissimus, Multifidus —
   nicht den Quadratus lumborum, nicht den Internus Obliquus, nicht Glute medius.
   Die QL-Aussagen stammen aus McGill 2009 bzw. dessen Aufarbeitung und sind
   qualitativ.
4. **Keine Studienlage zur Rotationsstabilität von Implements.** Die
   Kipp-Zeitkonstanten und die Implement-Rangfolge sind Herleitung plus
   Coach-Konsens. Ein einfacher Feldtest wäre möglich (Zeit bis erster Nachgriff,
   Anzahl Nachgriffe pro Satz, Haltezeit bei identischer Last über Implements
   hinweg) und würde die Rangfolge falsifizierbar machen.
5. **Nicht geklärt: ab welcher Last der Suitcase-Hold die 40-%-MVIC-Schwelle
   überschreitet.** Ellestad hat nur eine Laststufe getestet; eine
   Dosis-Wirkungs-Kurve Last → laterale Rumpfaktivierung existiert nicht. Die
   Aussage „grob doppelte Last nötig" ist eine lineare Extrapolation aus einem
   einzigen Punkt und entsprechend unsicher.
6. **Handgelenks-Momenttoleranz ist nicht quantifiziert.** Es gibt keine Evidenz
   dafür, welches Deviationsmoment eine in Rehabilitation befindliche
   Handgelenkssehne verträgt. Die Empfehlung ist deshalb kategorial
   (rotationsstabiles Implement) statt numerisch (N·m-Grenze) — das ist die
   ehrlichere Formulierung, aber sie liefert keinen Progressions-Parameter für die
   Rotationsachse.
7. **Ergonomie-Transfer.** Die zitierte Werkzeug-Ergonomie beschreibt
   arbeitsbezogene Dauerbelastung, nicht Trainings-Isometrie in Sätzen. Die
   Richtung des Effekts (Schwerpunkt außerhalb der Hand → mehr Handgelenks-/
   Unterarmarbeit) ist übertragbar; die Dosis-Wirkungs-Schwellen sind es nicht.
