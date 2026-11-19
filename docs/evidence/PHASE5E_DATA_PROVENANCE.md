# PHASE 5E — Data Provenance & Calibration Manifest

**Classification:** SYNTHETIC CALIBRATED ROUTING BENCHMARK  
**System:** DIRS (Disaster Incident Response System)

---

## 1. Provenance Classifications

All benchmark instances, coordinates, vehicle specifications, and time horizons utilized in Phase 5E optimization validation are synthetic-calibrated decision-support structures.

> [!CAUTION]
> **Claim Hygiene Rules:**
> 1. No real-time government vehicle tracking data is utilized.
> 2. No real government fleet or operational dispatch data is claimed.
> 3. No real disaster incident routes in Chennai or elsewhere are claimed.
> 4. All physical unit values are calibrated engineering estimates based on humanitarian logistics standards (SPHERE Handbook).

---

## 2. Commodity Conversion Calibration Table

| Commodity Category | Unit Weight (kg) | Unit Volume (m3) | Reference Calibration Source |
|---|---|---|---|
| `WATER` | 1.000 | 0.0010 | 1 Litre drinking water pack |
| `FOOD` | 0.500 | 0.0008 | Calibrated dry emergency ration pack |
| `MEDICAL_KITS` | 2.000 | 0.0050 | Trauma & first-aid disaster response kit |
| `RESCUE_EQUIPMENT` | 10.000 | 0.0500 | Heavy inflatable rafts, ropes, cutting tools |
| `SANITATION_KITS` | 1.500 | 0.0030 | Hygiene & sanitation family packs |
| `TEMPORARY_SHELTER_SUPPLIES` | 5.000 | 0.0200 | Tarpaulins, structural poles, bedding kits |

---

## 3. Vehicle Fleet Models (Phase 5B Schemas)
- Fleet types: `TRUCK` (3,000–4,000 kg, 15–20 m³), `VAN` (1,200 kg, 6 m³), `AMBULANCE` (500 kg, 2.5 m³).
- Eligibility Rule: Strictly `AVAILABLE` status. Any vehicle marked `MAINTENANCE`, `IN_TRANSIT`, `UNAVAILABLE`, or `ASSIGNED` is excluded.
