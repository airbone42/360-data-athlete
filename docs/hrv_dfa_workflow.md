# HRV DFA-Alpha1 Workflow

## 1. Datenquelle: Woher kommen RR-Intervalle?

### Ältere Sportuhren ohne native FIT-`hrv`-Message-Unterstützung

**Typisches Ergebnis: Kein RR-Export aus der FIT-Datei.**

Ältere Sportuhren (z.B. Garmin Forerunner 735XT) speichern bei ANT+-Verbindung zu einem externen HRM-Gurt **ausschliesslich** das epochengemittelte HR-Signal in `record`-Messages (1 Hz). Beat-to-beat `hrv`-Messages werden von der Firmware nicht geschrieben.

intervals.icu spiegelt das: Stream-Typ `rr_intervals` ist nicht vorhanden, nur `heartrate`.

### Verfügbare Alternativen für RR-Daten (externer HRM-Gurt, z.B. Polar H10)

| Quelle | Format | Methode |
|--------|--------|---------|
| **Polar Beat App** (iOS/Android) | CSV mit `rr_ms`-Spalte | Aufnahme starten, Session exportieren via "Trainings-Dateien exportieren" → CSV |
| **Fatmaxxer App** (Android) | CSV mit `rr`-Spalte | Open-Source App, direkte Bluetooth-LE-Verbindung zum Gurt, Export als CSV |
| **Elite HRV App** | CSV oder TXT | App verbindet direkt via BLE zum Gurt, exportiert RR-Series |
| **Neuere Garmin-Geräte** (Fenix 6+, FR945+) | FIT `hrv`-Messages | Schreiben `hrv`-Messages auch von ANT+-Gurten |

**Typische Lösung bei fehlender FIT-`hrv`-Unterstützung:** Parallel-Aufzeichnung über eine zweite App (z.B. Polar Beat) starten. Ein Polar H10 sendet gleichzeitig ANT+ (Uhr) und Bluetooth LE (App). Beide Geräte können gleichzeitig verbunden sein.

### FIT-Dateien mit hrv-Messages

Geräte, die `hrv`-Messages in FIT schreiben (mit externem HRM-Gurt via ANT+), beispielhaft:
- Garmin Fenix 6 / 6S / 6X
- Garmin Forerunner 945 / 955 / 965
- Garmin Forerunner 745
- Garmin Epix Gen 2

Ältere Forerunner-Modelle (z.B. 735XT) gehören **nicht** dazu.

---

## 2. Script: analyse_hrv_dfa.py

### Pfad
```
scripts/analyse_hrv_dfa.py
```

### Unterstützte Eingabeformate

| Format | Source-Typ | Spaltenname RR |
|--------|-----------|----------------|
| FIT mit `hrv`-Messages | `fit` | automatisch |
| Polar Beat CSV | `polar_csv` | `rr_ms` oder `RR Interval (ms)` |
| Fatmaxxer CSV | `polar_csv` | `rr` |
| Elite HRV TXT | `txt` | eine Zeile pro Wert |

### Ausgabe-Schema (JSON)

```json
{
  "dfa_alpha1": 0.8542,
  "vt1_estimate_bpm": 142.3,
  "rr_count": 1847,
  "rr_source": "polar_csv",
  "windows": [
    {
      "start_s": 0,
      "end_s": 120,
      "hr_avg": 128.4,
      "dfa_alpha1": 0.9821,
      "beat_count": 256
    }
  ]
}
```

**Felder:**
- `dfa_alpha1`: Globaler Alpha-1-Koeffizient über alle RR-Daten (Skalierungsexponent Box-Grössen 4–16 Schläge)
- `vt1_estimate_bpm`: HR-Wert (bpm) beim ersten Unterschreiten von DFA-α1 = 0.75 (linear interpoliert). `null` wenn Schwelle nicht erreicht.
- `rr_count`: Anzahl valider RR-Intervalle
- `rr_source`: Verwendete Datenquelle
- `windows`: Fensterwerte (Sliding Window, Standard: 120 s, 60 s Step)

---

## 3. FIT-Parser Erweiterung

Die Funktion `extract_rr_intervals()` in `app/utils/fit_parser.py` prüft FIT-Dateien auf hrv-Messages:

```python
from app.utils.fit_parser import extract_rr_intervals
rr = extract_rr_intervals(Path("/tmp/example/file.fit"))
# rr = [{"timestamp_s": 0.0, "rr_ms": 812.0}, ...]
# rr = []  wenn keine hrv-Messages vorhanden (ältere Sportuhren ohne hrv-Support)
```

---

## 4. Befehle

### Analyse aus FIT-Datei (sofern hrv-Messages vorhanden)
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/analyse_hrv_dfa.py --input /tmp/example/recovery_run_20250411.fit
```

### Analyse aus Polar Beat CSV
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/analyse_hrv_dfa.py --input /tmp/example/polar_rr_20250411.csv --source polar_csv
```

### Analyse aus Elite HRV / Fatmaxxer TXT
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/analyse_hrv_dfa.py --input /tmp/example/rr_data.txt --source txt
```

### Angepasste Fenstergrösse (empfohlen bei Recovery Runs)
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/analyse_hrv_dfa.py \
  --input /tmp/example/polar_rr_20250411.csv \
  --source polar_csv \
  --window-size 120 \
  --step 30
```

---

## 5. Python-Abhängigkeiten

Das Script benötigt **keine externen Bibliotheken** ausser `fitparse` (für FIT-Input).

| Bibliothek | Benötigt | Status |
|-----------|---------|--------|
| `fitparse` | Nur für FIT-Input | installiert |
| `numpy` | Nein — DFA in Pure Python | nicht installiert, nicht nötig |
| `scipy` | Nein | nicht installiert, nicht nötig |

Die DFA-Berechnung (Cumulative Sum, Detrending, RMS, Log-Regression) ist vollständig in reinem Python implementiert.

---

## 6. Wiederholte Analyse

Für jede Einheit mit RR-fähigem HRM-Gurt:
1. Parallel-Aufzeichnung (z.B. Polar Beat) starten
2. Nach der Einheit: CSV-Export aus der App
3. Analyse:
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/analyse_hrv_dfa.py \
  --input /tmp/example/polar_rr_YYYYMMDD.csv \
  --source polar_csv \
  --window-size 120 --step 30
```
4. VT1-Wert dokumentieren: `python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/post_message.py --date YYYY-MM-DD --note "DFA-alpha1: X.XX, VT1: YYY bpm"`
