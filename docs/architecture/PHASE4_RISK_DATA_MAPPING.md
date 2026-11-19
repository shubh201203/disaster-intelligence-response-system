# DIRS Phase 4 — Disaster Risk Real-World Data Mapping & Temporal Leakage Check

## Executive Summary & Final Verdict

- **Decision Choice:** **`READY`**
- **Primary Meteorological Dataset:** **NOAA Global Historical Climatology Network (GHCN) Daily + IMD High-Resolution Daily Weather Grids**
- **Primary Event Catalog Dataset:** **NOAA Storm Events Database + EM-DAT International Disaster Occurrence Catalog**
- **Spatial Grid Resolution:** 0.25° × 0.25° (~25 km × 25 km spatial cell)
- **Temporal Prediction Window:** 24-hour forward lookahead ($T \rightarrow T+24\text{h}$)

---

## 1. Spatial-Temporal Dataset Joining Architecture

The Risk Dataset is constructed by joining continuous station weather observations with verified historical disaster occurrence logs:

```text
NOAA GHCN / IMD Daily Weather Observations (Location, Date, Temp, Rain, Wind, Pressure)
                                   +
NOAA Storm Events / EM-DAT Event Catalog (Grid Cell, Event Start Time, Hazard Type)
                                   ↓
                   [Spatial Join: 0.25° Grid Cell]
                  [Temporal Join: Antecedent Window T-1]
                                   ↓
         Labeled Risk Dataset (Antecedent Features → Disaster Event Outcome)
```

---

## 2. Temporal Leakage Audit & Feature Filtering

To guarantee zero temporal leakage, all predictive features are restricted strictly to observations recorded **AT OR BEFORE** prediction time $T_{\text{pred}}$ (06:00 AM on Day $T$). Post-event measurements caused by the disaster itself are strictly excluded.

### Feature Classification Matrix:

| Feature Name | Source | Recorded Time | Allowed / Excluded | Reason |
| :--- | :--- | :---: | :---: | :--- |
| `rainfall_accumulated_mm_24h` | Weather Station | $T-24\text{h}$ to $T$ | **ALLOWED** | Antecedent 24-hour rainfall measured before prediction point. |
| `rainfall_accumulated_mm_72h` | Weather Station | $T-72\text{h}$ to $T$ | **ALLOWED** | 3-day antecedent soil saturation index measured before prediction. |
| `max_wind_speed_kmh_24h` | Weather Station | $T-24\text{h}$ to $T$ | **ALLOWED** | Maximum sustained wind velocity leading up to prediction time. |
| `min_barometric_pressure_hpa_24h` | Weather Station | $T-24\text{h}$ to $T$ | **ALLOWED** | Barometric pressure drop preceding storm arrival. |
| `river_water_level_m_antecedent` | Gauge Sensor | $T-6\text{h}$ | **ALLOWED** | Baseline river stage height before disaster surge. |
| `historical_disaster_frequency` | GIS Database | $< T$ | **ALLOWED** | Multi-year historical occurrence frequency for spatial grid cell. |
| `population_density_exp` | Census GIS | Prior Year | **ALLOWED** | Static demographic exposure density. |
| `elevation_m` | DEM Satellite | Static | **ALLOWED** | Spatial topography elevation. |
| `infrastructure_proximity_m` | GIS Layers | Static | **ALLOWED** | Distance to critical transport/power infrastructure. |
| *Disaster Property Damage ($)* | Post-Event Audit | $T+24\text{h}$ to $T+48\text{h}$ | **EXCLUDED** | **TEMPORAL LEAKAGE.** Post-disaster outcome. |
| *Emergency Rescue Calls Count* | Dispatch Logs | Day $T$ | **EXCLUDED** | **TEMPORAL LEAKAGE.** Triggered by disaster onset. |
| *Casualties / Death Toll* | Hospital Reports | Day $T+1$ | **EXCLUDED** | **TEMPORAL LEAKAGE.** Post-event consequence. |
| *Peak River Flood Surge (Day T+1)* | Gauge Sensor | Day $T+1$ | **EXCLUDED** | **TEMPORAL LEAKAGE.** Occurs after prediction window. |

---

## 3. Target Definition & Risk Class Mapping

- **Binary Event Indicator ($Y$):**  
  $Y = 1$ if a verified severe disaster event (flood, tropical cyclone landfall, major landslide) was recorded in the spatial grid cell during Day $T$.  
  $Y = 0$ if no disaster event occurred during Day $T$ despite active weather conditions.

- **Predicted Probability $P(Y=1 \mid \mathbf{X}_{<T})$ Mapping into DIRS Risk Levels:**
  - **`LOW` Risk:** $P < 0.15$
  - **`MODERATE` Risk:** $0.15 \le P < 0.45$
  - **`HIGH` Risk:** $0.45 \le P < 0.75$
  - **`EXTREME` Risk:** $P \ge 0.75$

---

## 4. Summary & Verification

The joined dataset provides a defensible predictive pipeline where input features $\mathbf{X}_{<T}$ precede target outcome $Y_T$ with zero temporal leakage. Target status: **`READY`**.
