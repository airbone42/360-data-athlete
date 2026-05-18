# Muskel-Datenbank (Framework-Default)

Sport-relevante Muskeln für Laufen (L), Radfahren (R), Bouldern (B), Ninja (N).
Rollen: P = Primary | S = Secondary | Stab = Stabilisator

## Regenerations-Gruppen

| Gruppe | RPE < 6 (low) | RPE 6–7 (mid) | RPE ≥ 8 (high) | Charakteristik |
|--------|--------------|---------------|----------------|----------------|
| small_dynamic | 24h | 48h | 72h | Kleine Muskeln, dynamisch (Unterarm, Wade) |
| small_tendon | 36h | 60h | 96h | Sehnen-dominant (Grip-Holds, Finger-Ext Band) |
| medium | 36h | 60h | 84h | Mittelgroß (Bizeps, Trizeps, Schulter, Bauch) |
| large | 48h | 72h | 96h | Groß (Quads, Glutes, Lats, Brust) |
| core_deep | 24h | 36h | 60h | Core Anti-Rotation, tief |
| plyo_cns | 48h | 72h | 120h | ZNS + Sehnen bei Plyometrie |

Decay: exponentiell — `fatigue_pct(h) = 100 × exp(-h / τ)` mit `τ = regen_hours / ln(4)`
Eccentric-Multiplier: 1.4 bei `eccentric_dominant: true` (Nordic Curl, Depth Drop, SL-RDL)

---

## Muskeln nach Körperteil

### Fuß / Sprunggelenk

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| tibialis_posterior | Hinterer Schienbeinmuskel | small_dynamic | P | Stab | S | S |
| flexor_hallucis_longus | Großzehen-Beuger | small_dynamic | P | — | P | Stab |
| peroneus_longus | Langer Wadenbeinmuskel | small_dynamic | S | Stab | S | S |
| peroneus_brevis | Kurzer Wadenbeinmuskel | small_dynamic | S | Stab | S | Stab |
| abductor_hallucis | Großzehen-Abspreizer | small_dynamic | S | — | S | — |

### Unterschenkel

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| gastrocnemius | Wade (oberflächlich) | small_dynamic | P | P | S | S |
| soleus | Wade (tief) | small_dynamic | P | P | S | S |
| tibialis_anterior | Vorderer Schienbeinmuskel | small_dynamic | S | Stab | Stab | S |
| flexor_digitorum_longus | Langer Zehenbeuger | small_dynamic | S | — | P | Stab |
| extensor_hallucis_longus | Großzehen-Strecker | small_dynamic | S | — | S | — |

### Oberschenkel anterior

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| rectus_femoris | Gerader Oberschenkelmuskel | large | P | P | S | P |
| vastus_lateralis | Äußerer Oberschenkelkopf | large | S | P | S | S |
| vastus_medialis | Innerer Oberschenkelkopf | large | S | P | S | S |
| vastus_intermedius | Mittlerer Oberschenkelkopf | large | S | P | — | S |

### Oberschenkel posterior

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| biceps_femoris_long | Langer Bizeps femoris | large | P | S | S | P |
| biceps_femoris_short | Kurzer Bizeps femoris | medium | S | S | — | S |
| semitendinosus | Halbsehniger Muskel | large | P | S | — | S |
| semimembranosus | Halbhäutiger Muskel | large | S | S | — | — |

### Hüfte / Gesäß

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| gluteus_maximus | Großer Gesäßmuskel | large | P | P | S | P |
| gluteus_medius | Mittlerer Gesäßmuskel | large | P | S | P | S |
| gluteus_minimus | Kleiner Gesäßmuskel | medium | Stab | Stab | S | Stab |
| piriformis | Birnenförmiger Muskel | medium | Stab | Stab | S | Stab |
| iliopsoas | Hüftbeuger | large | P | S | P | P |
| tensor_fasciae_latae | Schenkelbindenspanner | medium | Stab | Stab | S | Stab |

### Adduktoren

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| adductor_magnus | Großer Anzieher | large | S | P | S | S |
| adductor_longus | Langer Anzieher | medium | S | S | P | S |
| gracilis | Schlankmuskel | small_dynamic | Stab | Stab | Stab | Stab |

### Core ventral

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| rectus_abdominis | Gerader Bauchmuskel | core_deep | Stab | Stab | S | P |
| obliquus_externus | Äußerer schiefer Bauchmuskel | core_deep | Stab | Stab | P | P |
| obliquus_internus | Innerer schiefer Bauchmuskel | core_deep | Stab | Stab | P | S |
| transversus_abdominis | Querer Bauchmuskel | core_deep | Stab | Stab | Stab | Stab |

### Core dorsal

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| erector_spinae | Rückenstrecker | medium | Stab | Stab | S | S |
| multifidus | Vielgespaltener Muskel | core_deep | Stab | Stab | Stab | Stab |
| quadratus_lumborum | Quadratischer Lendenmuskel | medium | Stab | Stab | S | S |

### Rücken / Lats

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| latissimus_dorsi | Breiter Rückenmuskel | large | — | — | P | P |
| rhomboideus_major | Großer Rautenmuskel | medium | — | — | S | S |
| rhomboideus_minor | Kleiner Rautenmuskel | medium | — | — | S | S |
| trapezius_mid | Trapezmuskel (Mitte) | medium | Stab | Stab | S | S |
| trapezius_lower | Trapezmuskel (unten) | medium | Stab | Stab | P | Stab |

### Trapezius oberer Anteil

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| trapezius_upper | Trapezmuskel (oben) | medium | Stab | Stab | Stab | Stab |

### Brust

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| pectoralis_major_clavicular | Brustmuskel (Schlüsselbein-Anteil) | large | — | — | S | P |
| pectoralis_major_sternal | Brustmuskel (Sternum-Anteil) | large | — | — | S | P |
| serratus_anterior | Sägemuskel | medium | — | — | S | S |

### Schulter

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| deltoideus_anterior | Vordere Schulter | medium | — | — | S | P |
| deltoideus_medius | Mittlere Schulter | medium | — | — | S | S |
| deltoideus_posterior | Hintere Schulter | medium | — | — | P | S |
| supraspinatus | Obergrätenmuskel (Rotatorenmanschette) | medium | — | — | Stab | Stab |
| infraspinatus | Untergrätenmuskel (Rotatorenmanschette) | medium | — | — | Stab | Stab |
| teres_minor | Kleiner runder Armmuskel | medium | — | — | Stab | S |

### Oberarm

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| biceps_brachii | Zweiköpfiger Bizeps | medium | — | — | P | P |
| brachialis | Armbeuger | medium | — | — | P | S |
| brachioradialis | Speichenmuskel | medium | — | — | P | S |
| triceps_brachii | Dreiköpfiger Trizeps | medium | — | — | S | P |
| teres_major | Großer runder Armmuskel | medium | — | — | S | S |

### Unterarm Flexoren (Grip / Handgelenk-Beugung)

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| flexor_digitorum_superficialis | Oberflächlicher Fingerbeuger | small_tendon | — | — | P | P |
| flexor_digitorum_profundus | Tiefer Fingerbeuger | small_tendon | — | — | P | P |
| flexor_pollicis_longus | Langer Daumenbeuger | small_tendon | — | — | S | S |
| flexor_carpi_radialis | Speichenseitiger Handbeuger | small_dynamic | — | — | Stab | S |
| flexor_carpi_ulnaris | Ellenseitiger Handbeuger | small_dynamic | — | — | Stab | S |
| pronator_teres | Runder Einwärtsdreher | small_dynamic | — | — | Stab | Stab |

### Unterarm Extensoren (Handgelenk-Streckung)

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| extensor_digitorum | Gemeinsamer Fingerstrecker | small_dynamic | — | — | Stab | S |
| extensor_carpi_radialis_longus | Langer speichenseitiger Handstrecker | small_dynamic | — | — | Stab | S |
| extensor_carpi_radialis_brevis | Kurzer speichenseitiger Handstrecker | small_dynamic | — | — | Stab | S |
| extensor_carpi_ulnaris | Ellenseitiger Handstrecker | small_dynamic | — | — | Stab | S |
| supinator | Auswärtsdreher | small_dynamic | — | — | Stab | Stab |

### Hand / Finger intrinsisch

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| lumbricales_interossei | Lumbrikalen + Interossei | small_tendon | — | — | P | S |
| opponens_pollicis | Daumengegensteller | small_tendon | — | — | P | S |
| abductor_pollicis | Daumenabspreizer | small_tendon | — | — | S | Stab |

### Nacken

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| sternocleidomastoideus | Kopfnicker | small_dynamic | Stab | Stab | Stab | Stab |
| scalenus | Treppenmuskel | small_dynamic | Stab | Stab | Stab | Stab |

### Knie / Hüfte Stabilisatoren

| ID | Name (DE) | Regen-Gruppe | L | R | B | N |
|----|-----------|--------------|---|---|---|---|
| popliteus | Kniekehlenmuskel | small_dynamic | Stab | Stab | S | Stab |
| obturator_internus | Innerer Hüftlochmuskel | small_dynamic | Stab | Stab | S | Stab |

---

## Anmerkungen

- **Grip-Holds (Farmer Hold, Dead Hang):** regen_group `small_tendon` — Sehnen (A2/A4-Pulley) erholen langsamer als Muskeln
- **Plyometrische Belastung:** eccentric_mult 1.4 addiert; ZNS-Recovery dominiert bei intensiver Plyo
- **Schulter-Overhead (Supraspinatus, Infraspinatus):** Volumen reduzieren wenn `athlete_static.md` Risikozonen eine Schulter-Sperre/Beobachtung listet
- **Sport-Relevanz:** P=direkt leistungslimitierend, S=unterstützend, Stab=Gelenk-Schutz, —=vernachlässigbar
