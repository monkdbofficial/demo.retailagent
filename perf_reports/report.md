# MonkDB / Trent — Test Report

**Timestamp:** 2025-09-26T15:51:46

**Table:** `trent.products`

**CSV:** `datasets/_sample_products.csv`

**WHERE:** `1=1`
## 1) Accuracy
| Metric | CSV | SQL | Δ | Tol | Pass |
|---|---:|---:|---:|---:|:--:|
| products | 100000 | 100000.0 | 0.0 | 0.0 | ✅ |
| avg_price | 1689.78 | 1689.78 | 0.0 | 1e-06 | ✅ |
| avg_mrp | 2209.78 | 2209.78 | 0.0 | 1e-06 | ✅ |
| avg_discount_pct | 21.22 | 21.22 | 0.0 | 1e-06 | ✅ |
| no_discount_items | 15016 | 15016.0 | 0.0 | 0.0 | ✅ |

**Discount bands:**

| Band | CSV | SQL | Δ | Pass |
|---|---:|---:|---:|:--:|
| 0% | 15019 | 15019 | 0 | ✅ |
| 0-20% | 35288 | 35269 | -19 | ❌ |
| 20-40% | 35293 | 35298 | 5 | ❌ |
| 40-60% | 13690 | 13704 | 14 | ❌ |
| 60%+ | 710 | 710 | 0 | ✅ |

**Brand concentration (top):**

| Brand | CSV Items | SQL Items | Δ Items | CSV Share % | SQL Share % | Δ Share | Pass |
|---|---:|---:|---:|---:|---:|---:|:--:|
| 20Dresses | 65970 | 65970 | 0 | 65.97 | 65.97 | 0.0 | ✅ |
| 250 DESIGNS | 2017 | 2017 | 0 | 2.02 | 2.02 | 0.0 | ✅ |
| 4711 | 13005 | 13005 | 0 | 13.0 | 13.01 | 0.01 | ✅ |
| 4WRD by Dressberry | 3033 | 3033 | 0 | 3.03 | 3.03 | 0.0 | ✅ |
| 9shines Label | 8957 | 8957 | 0 | 8.96 | 8.96 | 0.0 | ✅ |
| A Homes Grace | 7018 | 7018 | 0 | 7.02 | 7.02 | 0.0 | ✅ |

**Row parity sample:** skipped (no valid PK rows after dropna/drop_duplicates)

## 2) Performance (latency in ms)

### KPIs

| p50 | p95 | p99 | min | max | repeats |
|---:|---:|---:|---:|---:|---:|
| 774.71 | 875.54 | 1075.49 | 679.91 | 1125.48 | 20 |

### Discount Bands

| p50 | p95 | p99 | min | max | repeats |
|---:|---:|---:|---:|---:|---:|
| 748.31 | 929.81 | 1001.17 | 689.96 | 1019.01 | 20 |

### Brand Share

| p50 | p95 | p99 | min | max | repeats |
|---:|---:|---:|---:|---:|---:|
| 807.79 | 938.95 | 1006.18 | 658.58 | 1022.98 | 20 |
