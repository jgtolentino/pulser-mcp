# Synthetic Data Generator MCP V2 - PH Retail Dataset Expansion

Generates realistic Philippine retail transaction data with accurate TBWA client footprint (55% market share), category-based distribution, economic weighting by region/city, and authentic barangay-level locations.

## Features

- **Accurate Market Share**: Category-based distribution matching real PH retail landscape
  - Dairy: 13% (Alaska 90% dominance) 
  - Snacks: 15% (Oishi 85% dominance)
  - Beverages: 10% (Del Monte partial share)
  - Home Care: 10% (Peerless 80% dominance)
  - Tobacco: 18% (JTI 40% share)
  - Total TBWA: 55% of market
- **Economic Weighting**: Transaction density based on regional GDP and urbanity
  - NCR: 3.5x baseline (highest)
  - Major cities: 1.5-2.5x
  - Rural areas: 0.7-1.0x
- **Coverage-First**: Guarantees all 17 regions have representation
- **Authentic Geography**: 500+ real barangays, 1000+ Filipino sari-sari stores
- **Time Patterns**: Peak hours, payday surges, weekend patterns
- **Quality Validation**: Completeness, distribution, outlier detection

## Quick Start

1. **Setup**:
   ```bash
   cd tools/js/mcp/synthetic_data_mcp
   ./scripts/setup.sh
   ```

2. **Start Server** (V2 with accurate market share):
   ```bash
   ./scripts/start_v2.sh
   ```
   
   Or manually:
   ```bash
   source venv/bin/activate
   python src/synthetic_server_v2.py
   ```

3. **Generate Scout-Ready Data** (17,000 rows, ~6MB):
   ```bash
   python scripts/generate_scout_ready.py
   ```
   
   Or custom generation:
   ```bash
   python scripts/generate_sample.py
   ```

## Market Share Distribution

| Category | Market % | TBWA Client | TBWA Dominance | Contribution |
|----------|----------|-------------|----------------|-------------|
| Dairy/Creamer | 13% | Alaska | 90% | 11.7% |
| Snacks | 15% | Oishi | 85% | 12.8% |
| Beverages | 10% | Del Monte | 40% | 4.0% |
| Condiments | 3% | Del Monte | 85% | 2.6% |
| Canned | 2% | Del Monte | 90% | 1.8% |
| Home Care | 10% | Peerless | 80% | 8.0% |
| Personal Care | 6% | Peerless | 75% | 4.5% |
| Tobacco | 18% | JTI | 40% | 7.2% |
| Other FMCG | 23% | None | 0% | 0% |
| **Total** | **100%** | | | **≈55%** |

### Brands (57 total)
- **TBWA Clients (39)**: 
  - Alaska (6): Evap, Condensed, Powdered, Krem-Top, Alpine, Cow Bell
  - Oishi (12): Prawn Crackers, Pillows, Marty's, Ridges, etc.
  - Peerless (6): Champion, Calla, Hana, Cyclone, Pride, Care Plus
  - Del Monte (8): Pineapple, Tomato, Spaghetti Sauce, Fruit Cocktail, etc.
  - JTI (7): Winston, Camel, Mevius, LD, Mighty, Caster, Glamour
- **Competitors (18)**: Nestlé, Unilever, P&G, Coca-Cola, PMFTC

### Geographic Distribution
- **17 Regions**: Weighted by economic activity
  - Tier 1 (2.5x+): NCR, Region IV-A
  - Tier 2 (1.5-2.4x): Regions III, VII, XI
  - Tier 3 (1.0-1.4x): Regions I, V, VI, X, XII, CAR
  - Tier 4 (<1.0x): Regions II, VIII, IX, XIII, IV-B, BARMM
- **145+ Cities**: Additional multipliers (Makati 1.8x, BGC 1.6x)
- **500+ Barangays**: Real names (Tondo, Binondo, etc.)
- **1000+ Stores**: Authentic Filipino names (Aling Rosa's, Mang Pedro's)

### Products (150+ SKUs)
- Real pack sizes: Alaska Evap 370ml, Oishi Prawn 90g
- Accurate MSRPs: ₱8-300 range
- Tobacco packs: Winston 20s ₱140, Marlboro 20s ₱160

## Available Tools

### generate_data
Generate realistic transaction data:
```json
{
  "tool": "generate_data",
  "params": {
    "dataset_type": "transactions",
    "num_records": 100000,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "client_weight": 0.55,
    "tobacco_share": 0.18,
    "output_format": "csv"
  }
}
```

### validate_quality
Check data quality:
```json
{
  "tool": "validate_quality",
  "params": {
    "dataset_path": "output/transactions_20241215_143022.csv",
    "validation_rules": ["completeness", "distribution", "outliers"]
  }
}
```

### simulate_scenario
Model market scenarios:
```json
{
  "tool": "simulate_scenario",
  "params": {
    "scenario": "peak_season",
    "duration_days": 30,
    "impact_factor": 1.5,
    "affected_brands": ["Alaska", "Del Monte"]
  }
}
```

## Data Schema

### Transaction Record
```csv
txn_id,datetime,store_id,store_name,sku_id,sku_name,brand_id,brand_name,
category,quantity,unit_price,total_amount,barangay,city,province,region,is_tbwa_client
```

### Geographic Hierarchy
```
Region → Province → City/Municipality → Barangay → Store
NCR → Metro Manila → Manila → Tondo → Aling Rosa's Sari-Sari Store
```

## Market Patterns

### Time-Based
- **Peak Hours**: 6-9am, 5-8pm (higher volume)
- **Payday Surge**: 15th & 30th (+40% volume)
- **Weekend Boost**: Sat/Sun (+25% volume)

### Category Mix
- **FMCG**: 82% of transactions
- **Tobacco**: 18% of transactions
  - JTI brands: 40% of tobacco (7.2% total)
  - PMFTC & others: 60% of tobacco (10.8% total)

### Regional Variations
- **Urban (NCR, Cebu, Davao)**: More premium brands
- **Provincial**: Higher value brand preference
- **Mindanao**: Adjusted product mix

## Validation Metrics

### Completeness Score
```python
completeness = 1 - (null_count / total_cells)
# Target: > 99%
```

### Distribution Check
```python
# Brand share validation
tbwa_share = tbwa_revenue / total_revenue
# Expected: 0.55 ± 0.02

# Tobacco share validation  
tobacco_share = tobacco_txns / total_txns
# Expected: 0.18 ± 0.01
```

### Geographic Coverage
```python
# All regions represented
regions_covered = unique_regions / 17
# Target: 100%
```

## Use Cases

### 1. Scout Dashboard Testing
```bash
# Generate 1M transactions for stress testing
generate_data --records 1000000 --format parquet
```

### 2. Market Analysis
```bash
# Christmas season simulation
simulate_scenario --scenario peak_season \
  --start "2024-12-01" --end "2024-12-31" \
  --impact 1.8
```

### 3. Regional Expansion
```bash
# Focus on Visayas data
generate_data --regions "Region VI,Region VII" \
  --records 50000
```

## Best Practices

1. **Batch Generation**: Use 10K-100K records per batch
2. **Date Ranges**: Keep within 1 year for realism
3. **Validation**: Always validate after generation
4. **Scenario Testing**: Use scenarios for edge cases

## Advanced Configuration

### Custom Brand Weights
```python
# Adjust individual brand probabilities
BRAND_WEIGHTS = {
    "Alaska": 0.15,    # 15% of TBWA share
    "Oishi": 0.20,     # 20% of TBWA share
    "Winston": 0.40    # 40% of tobacco share
}
```

### Store Density
```python
# Stores per barangay
STORE_DENSITY = {
    "urban": 3.5,      # NCR, major cities
    "suburban": 2.0,   # Provincial cities
    "rural": 1.2       # Remote areas
}
```

## Troubleshooting

- **Memory Issues**: Reduce batch size or use parquet format
- **Slow Generation**: Enable multiprocessing in config
- **Invalid Geography**: Update locations_master.csv
- **Price Anomalies**: Check sku_catalog.csv MSRPs

## Data Export

### For Supabase
```bash
# Generate and prepare for upload
generate_data --format csv --records 100000
# Upload via Supabase CLI or API
```

### For Analytics
```bash
# Parquet for big data tools
generate_data --format parquet --compress snappy
```

## License

Part of InsightPulseAI SKR - Proprietary