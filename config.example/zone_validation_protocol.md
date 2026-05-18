# Zonen-Validierung mit Polar H10 (DFA-α1-Methode)

Wenn die Zonen unsicher sind (siehe Trigger unten), erhält der Athlet beim nächsten Z2-Lauf den Hinweis, einen **Brustgurt mit RR-Daten-Export** (z.B. Polar H10) statt eines wrist-/optischen HF-Sensors zu verwenden. Mit einem solchen Sensor kann via DFA-α1 (Detrended Fluctuation Analysis) die aerobe (VT1) und anaerobe Schwelle (VT2/LTHR) im Training validiert werden.

**Wissenschaft:** DFA-α1 = 0.75 → VT1 (±4–7 bpm Genauigkeit, r > 0.88); DFA-α1 = 0.5 → VT2/LTHR (r ≈ 0.85). Beide Schwellen in einem Lauf erfassbar (Rogers et al. 2021, Doerr et al. 2021).

**Trigger für H10-Empfehlung** (einer genügt):
- Letzte Zonen-Validierung (`lastZoneValidation` in athlete_status.md) > 10 Wochen zurück
- Trainingspause > 3 Wochen (implizite Schwellenverschiebung)
- CTL-Zuwachs > 15% seit letzter Validierung
- Athlet meldet: „Z2 fühlt sich zu leicht / zu schwer an"
- Wiederaufbau nach Verletzung/Krankheit (> 2 Wochen Pause)

**Testprotokoll:**
1. RR-fähigen Brustgurt anlegen, 10–15 min vor Test befeuchten
2. DFA-α1-Live-App (z.B. Fatmaxxer für Android/iOS) → Brustgurt via BLE verbinden → DFA-α1 live anzeigen
3. Lauf: 10 min Einlaufen Z1, dann alle 3–5 min Pace um ~10 s/km steigern bis über LTHR
4. DFA-α1 = 0.75: aerobe Schwelle (neue Z2-Obergrenze); DFA-α1 = 0.5: LTHR (neue Z4-Obergrenze)
5. Post-hoc-Analyse: RR-Daten aus der Gurt-App exportieren → Kubios HRV (kostenlos) für präzise Auswertung

**Wann wiederholen:** alle 8–10 Wochen, nach Pausen > 3 Wochen, nach CTL-Sprung > 15%.
