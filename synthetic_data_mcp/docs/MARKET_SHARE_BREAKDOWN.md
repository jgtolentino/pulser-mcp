# Market Share Breakdown - PH Sari-Sari Retail Landscape

## Total Market Composition

| Macro-category            | % of All Transactions | TBWA Client         | TBWA Share in Category | TBWA Contribution to Total |
|---------------------------|----------------------|---------------------|------------------------|---------------------------|
| **Dairy / Coffee Creamer**    | **13%**              | Alaska Milk Corp    | 90%                    | **11.7%**                 |
| **Snacks & Confectionery**    | **15%**              | Oishi / Liwayway    | 85%                    | **12.8%**                 |
| **Beverages & Condiments**    | **12%**              | Del Monte PH        | 85%                    | **10.2%**                 |
| **Home & Personal Care**      | **16%**              | Peerless           | 80%                    | **12.8%**                 |
| **Tobacco**                   | **18%**              | JTI                | 40%                    | **7.2%**                  |
| **Subtotal - TBWA Clients**   | —                    | —                   | —                      | **54.7% ≈ 55%**           |
| **Other FMCG**                | **26%**              | Competitors only    | 0%                     | **26%**                   |
| **Grand Total**               | **100%**             | —                   | —                      | **100%**                  |

## TBWA Client Breakdown

### Alaska Milk Corporation (6 brands)
- Alaska Evaporated Milk
- Alaska Condensed Milk
- Alaska Powdered Milk
- Krem-Top (Coffee Creamer)
- Alpine
- Cow Bell

**Dominance**: 90% of Dairy category, 95% of Coffee Creamer

### Oishi / Liwayway Marketing (12 brands)
- Oishi Prawn Crackers
- Oishi Pillows
- Oishi Marty's
- Oishi Ridges
- Oishi Bread Pan
- Oishi Gourmet Picks
- Oishi Crispy Patata
- Oishi Smart C+
- Oaties
- Hi-Ho
- Rinbee
- Deli Mex

**Dominance**: 85% of Snacks category

### Del Monte Philippines (8 brands)
- Del Monte Pineapple Juice
- Del Monte Tomato Products
- Del Monte Spaghetti Sauce
- Del Monte Fruit Cocktail
- Del Monte Pasta
- S&W
- Today's
- Fit 'n Right

**Dominance**: 85% of Condiments, 90% of Canned Fruits, 40% of Beverages

### Peerless Products Manufacturing (6 brands)
- Champion (Detergent)
- Calla (Bleach)
- Hana (Shampoo)
- Cyclone (Insecticide)
- Pride (Detergent Bar)
- Care Plus (Personal Care)

**Dominance**: 80% of Home Care, 75% of Personal Care

### Japan Tobacco International (7 brands)
- Winston
- Camel
- Mevius
- LD
- Mighty
- Caster
- Glamour

**Dominance**: 40% of Tobacco category

## Regional Distribution Weights

Based on economic factors, urbanity, and population density:

### Tier 1 - Highest Activity (Weight 2.5+)
- **NCR**: 3.5 (Metro Manila - highest density)
- **Region IV-A**: 2.5 (CALABARZON industrial belt)

### Tier 2 - Major Urban Centers (Weight 1.5-2.4)
- **Region III**: 2.0 (Central Luzon, Angeles/Clark)
- **Region VII**: 2.0 (Cebu metro area)
- **Region XI**: 1.8 (Davao growth center)

### Tier 3 - Standard Markets (Weight 1.0-1.4)
- **Region X**: 1.3 (Northern Mindanao, CDO)
- **CAR**: 1.2 (Baguio tourism)
- **Region VI**: 1.2 (Western Visayas)
- **Region I**: 1.0 (Ilocos baseline)
- **Region V**: 1.0 (Bicol standard)
- **Region XII**: 1.0 (SOCCSKSARGEN)

### Tier 4 - Rural/Lower Activity (Weight < 1.0)
- **Region IX**: 0.9 (Zamboanga Peninsula)
- **Region XIII**: 0.9 (Caraga)
- **Region II**: 0.8 (Rural Cagayan Valley)
- **Region VIII**: 0.8 (Eastern Visayas rural)
- **Region IV-B**: 0.8 (MIMAROPA islands)
- **BARMM**: 0.7 (Lowest economic activity)

## City-Level Multipliers (within regions)

### Premium Urban Centers
- Makati: 1.8x
- Taguig (BGC): 1.6x
- Cebu City: 1.5x
- Pasig (Ortigas): 1.4x
- Davao City: 1.4x

### Standard Urban
- Quezon City: 1.3x
- Mandaluyong: 1.3x
- Angeles City: 1.3x
- Manila: 1.2x
- Baguio City: 1.2x

### Lower Income Urban
- Caloocan: 0.9x
- Other unlisted cities: 1.0x (baseline)

## Implementation Notes

1. **Category Selection**: Transactions first select a category based on CATEGORY_WEIGHTS
2. **Brand Selection**: Within each category, TBWA clients are selected based on TBWA_CATEGORY_DOMINANCE
3. **Location Weighting**: Transactions are distributed based on REGIONAL_WEIGHTS × CITY_MULTIPLIERS
4. **Coverage First**: Algorithm ensures minimum representation for all regions before applying weights
5. **Time Patterns**: 
   - Peak hours: 6-9am, 5-8pm (1.5x volume)
   - Payday surge: 15th & 30th (1.4x volume)
   - Weekend boost: Saturday/Sunday (1.25x volume)

## Validation Targets

- TBWA Total Share: 55% ± 2%
- Tobacco Incidence: 18% ± 1%
- JTI within Tobacco: 40% ± 3%
- Regional Coverage: 100% (all 17 regions)
- Data Quality Score: >99% completeness