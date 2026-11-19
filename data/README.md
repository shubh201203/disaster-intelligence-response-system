# DIRS Phase 4 — Data Pipeline & Storage Specification

This directory manages all raw, interim, processed, and metadata assets for DIRS Phase 4 Real-World AI Model Upgrade.

## Directory Structure

```text
data/
├── raw/                      # Unmodified source datasets (OpenFEMA, NOAA, IMD, xBD, CrisisMMD)
│   ├── fema/
│   ├── noaa/
│   ├── imd/
│   ├── xbd/
│   └── crisismmd/
├── interim/                  # Cleaned, deduplicated, and spatially/temporally joined interim tables
├── processed/                # Fully preprocessed, feature-engineered NumPy/Pandas datasets ready for training
│   ├── severity_real.npz
│   ├── risk_real.npz
│   ├── cv_real.npz
│   └── resource_calibrated.npz
├── metadata/                 # Provenance metadata, dataset manifests, perceptual hash registries
│   ├── data_manifest.json
│   └── hash_registry.json
└── README.md
```

## Immutable Data Governance Principles
1. **Raw Data Protection:** Files in `data/raw/` are NEVER modified directly by any script.
2. **Reproducibility:** All processing steps from `data/raw/` to `data/processed/` are executed deterministically by `scripts/ingest_real_world_data.py`.
3. **Leakage Protection:** Spatial and temporal split metadata is stored in `data/metadata/` to ensure zero train/test contamination.
