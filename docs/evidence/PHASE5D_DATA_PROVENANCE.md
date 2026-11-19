# DIRS Phase 5D — Data Provenance & Calibration Document

## 1. Classification
**Classification:** SYNTHETIC CALIBRATED OPTIMIZATION BENCHMARK (DIRS-50)

## 2. Standardized Humanitarian Calibration Standards
The synthetic dataset generator (`app/ai/optimization/benchmark_dataset.py`) calibrates commodity demands against standard Sphere Project Humanitarian Guidelines:

- **WATER:** 15–20 Liters per person per day (clean drinking & hygiene water).
- **FOOD:** 2,100 kcal per person per day (ready-to-eat rations).
- **MEDICAL_KITS:** Emergency Trauma & First Aid kits per 100 casualties.
- **RESCUE_EQUIPMENT:** Inflatable rafts, hydraulic cutters, life jackets per rescue crew.
- **SANITATION_KITS:** Hygiene kits, water purification tablets per household.
- **TEMPORARY_SHELTER_SUPPLIES:** Tarpaulins, tents, blankets per displaced family.

## 3. Geographic Calibration Bounding Box
- **Bounding Box:** Coastal Chennai / Tamil Nadu (Lat: 12.65°N – 13.15°N, Lng: 79.95°E – 80.30°E).
- **Depot Locations:** 25 regional logistics stockpiles (MGR Central Storage Depot, Guindy Logistics Center, Tambaram Relief Stockpile, etc.).
- **Incident Locations:** 50 simulated disaster sites spanning Flood, Cyclone, Landslide, and Fire events.
