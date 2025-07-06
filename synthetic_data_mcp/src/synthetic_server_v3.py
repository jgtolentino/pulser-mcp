#!/usr/bin/env python3
"""
Synthetic Data Generator MCP Server V3 - Realistic PH Retail Market Share
Generates retail transaction data with accurate market representation
Based on actual sari-sari store category mix and TBWA client penetration
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, date
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import pandas as pd
import numpy as np
from faker import Faker
import random
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Faker for PH locale
fake = Faker('en_PH')

# FastAPI app
app = FastAPI(title="Synthetic Data Generator MCP Server V3 - Realistic Market Share")

# Data directories
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# REALISTIC Category weights based on sari-sari store transaction data
CATEGORY_WEIGHTS = {
    'Dairy': 0.07,           # 7% - Milk products
    'Coffee Creamer': 0.01,  # 1% - Part of dairy segment
    'Snacks': 0.14,          # 14% - Chips, crackers, biscuits combined
    'Beverage': 0.09,        # 9% - Non-CSD drinks (juice, water, energy)
    'CSD': 0.07,             # 7% - Carbonated soft drinks
    'Noodles': 0.06,         # 6% - Instant noodles
    'Pasta': 0.01,           # 1% - Spaghetti pasta
    'Tobacco': 0.14,         # 14% - Cigarettes
    'Home Care': 0.08,       # 8% - Laundry, cleaning
    'Personal Care': 0.06,   # 6% - Shampoo, soap, deo
    'Condiment': 0.04,       # 4% - Sauces, seasonings
    'Canned': 0.03,          # 3% - Canned goods
    'Rice': 0.07,            # 7% - Rice
    'Coffee': 0.03,          # 3% - Coffee products
    'Confectionery': 0.03,   # 3% - Candy, chocolate
    'Alcohol': 0.04,         # 4% - Beer, spirits
    'Other': 0.03            # 3% - Pet food, batteries, etc.
}

# REALISTIC TBWA client share within each category
TBWA_CATEGORY_SHARE = {
    'Dairy': 0.50,           # Alaska has ~50% of dairy
    'Coffee Creamer': 0.95,  # Alaska Krem-Top dominates
    'Snacks': 0.35,          # Oishi has ~35% vs URC, Monde Nissin
    'Beverage': 0.20,        # Del Monte + Oishi ~20% vs Coke, others
    'CSD': 0.0,              # No TBWA presence in CSD
    'Noodles': 0.0,          # No TBWA presence (Lucky Me dominates)
    'Pasta': 0.10,           # Del Monte pasta small share
    'Tobacco': 0.40,         # JTI 40% share
    'Home Care': 0.12,       # Peerless ~12% vs P&G, Unilever
    'Personal Care': 0.10,   # Peerless ~10% vs majors
    'Condiment': 0.40,       # Del Monte sauces ~40% share
    'Canned': 0.70,          # Del Monte fruit cocktail strong
    'Rice': 0.0,             # No TBWA presence
    'Coffee': 0.0,           # No TBWA presence
    'Confectionery': 0.0,    # No TBWA presence
    'Alcohol': 0.0,          # No TBWA presence
    'Other': 0.0             # No TBWA presence
}

# Calculate expected total TBWA share
def calculate_total_tbwa_share():
    total = 0
    for category, cat_weight in CATEGORY_WEIGHTS.items():
        tbwa_share = TBWA_CATEGORY_SHARE.get(category, 0)
        total += cat_weight * tbwa_share
    return total

# This should be ~22% based on realistic market data
EXPECTED_TBWA_SHARE = calculate_total_tbwa_share()
logger.info(f"Expected total TBWA market share: {EXPECTED_TBWA_SHARE:.1%}")

# Regional economic weights (urbanity, population density, income)
REGIONAL_WEIGHTS = {
    'NCR': 3.5,             # Highest urban density, income
    'Region III': 2.0,      # Central Luzon urban centers
    'Region IV-A': 2.5,     # CALABARZON industrial
    'Region VII': 2.0,      # Cebu metro area
    'Region XI': 1.8,       # Davao growth center
    'CAR': 1.2,             # Baguio tourism
    'Region I': 1.0,        # Ilocos baseline
    'Region II': 0.8,       # Rural Cagayan Valley
    'Region V': 1.0,        # Bicol standard
    'Region VI': 1.2,       # Western Visayas
    'Region VIII': 0.8,     # Eastern Visayas rural
    'Region IX': 0.9,       # Zamboanga Peninsula
    'Region X': 1.3,        # Northern Mindanao CDO
    'Region XII': 1.0,      # SOCCSKSARGEN
    'Region XIII': 0.9,     # Caraga
    'BARMM': 0.7,           # Lowest economic activity
    'Region IV-B': 0.8      # MIMAROPA islands
}

# City economic multipliers within regions
CITY_MULTIPLIERS = {
    # NCR cities
    'Makati': 1.8,          # CBD premium
    'Taguig': 1.6,          # BGC area
    'Manila': 1.2,          # Dense traditional
    'Quezon City': 1.3,     # Large mixed areas
    'Pasig': 1.4,           # Ortigas business
    'Caloocan': 0.9,        # Lower income
    'Mandaluyong': 1.3,     # Mixed commercial
    
    # Regional cities
    'Cebu City': 1.5,       # Major urban center
    'Davao City': 1.4,      # Growth center
    'Angeles City': 1.3,    # Clark influence
    'Baguio City': 1.2,     # Tourist economy
    'Tagaytay': 1.1,        # Weekend economy
    
    # Default for unlisted cities
    'default': 1.0
}

# Pydantic models
class GenerationRequest(BaseModel):
    dataset_type: str = "transactions"
    num_records: int = 17000
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    output_format: str = "csv"
    coverage_first: bool = True

class DataQualityRequest(BaseModel):
    dataset_path: str
    validation_rules: Optional[List[str]] = ["completeness", "distribution", "outliers"]

class MarketSimulationRequest(BaseModel):
    scenario: str
    duration_days: int = 30
    affected_brands: Optional[List[str]] = []
    impact_factor: float = 1.2

# Load master data
def load_master_data():
    """Load brand, product, and location data"""
    try:
        # Try to load extended data first
        brands_path = DATA_DIR / "brands_extended.csv"
        sku_path = DATA_DIR / "sku_catalog_extended.csv"
        
        if not brands_path.exists():
            brands_path = DATA_DIR / "brands.csv"
        if not sku_path.exists():
            sku_path = DATA_DIR / "sku_catalog.csv"
            
        locations_path = DATA_DIR / "locations_master.csv"
        
        if brands_path.exists() and sku_path.exists() and locations_path.exists():
            brands_df = pd.read_csv(brands_path)
            sku_df = pd.read_csv(sku_path)
            locations_df = pd.read_csv(locations_path)
            
            # Map old categories to new ones if needed
            category_mapping = {
                'Dairy': 'Dairy',
                'Coffee Creamer': 'Coffee Creamer',
                'Snacks': 'Snacks',
                'Beverage': 'Beverage',
                'Home Care': 'Home Care',
                'Personal Care': 'Personal Care',
                'Condiment': 'Condiment',
                'Canned': 'Canned',
                'Canned Fruit': 'Canned',
                'Food': 'Other',
                'Tobacco': 'Tobacco',
                'Pasta': 'Pasta',
                'Noodles': 'Noodles',
                'Coffee': 'Coffee',
                'CSD': 'CSD',
                'Alcohol': 'Alcohol',
                'Baby Care': 'Personal Care',
                'Pet Food': 'Other',
                'Hardware': 'Other',
                'Cooking Oil': 'Other',
                'Spreads': 'Other',
                'Frozen': 'Other',
                'Meat': 'Other',
                'Cereal': 'Other',
                'Confectionery': 'Confectionery',
                'Baking': 'Other',
                'Rice': 'Rice',
                'Sugar': 'Other'
            }
            
            brands_df['category'] = brands_df['category'].map(lambda x: category_mapping.get(x, 'Other'))
            
            return brands_df, sku_df, locations_df
        else:
            raise FileNotFoundError("Master data files not found")
            
    except Exception as e:
        logger.error(f"Error loading master data: {e}")
        raise

# Initialize master data
BRANDS_DF, SKU_DF, LOCATIONS_DF = load_master_data()

# Build brand lookup by category and client status
def build_brand_lookups():
    lookups = {}
    for cat in CATEGORY_WEIGHTS.keys():
        lookups[cat] = {
            'tbwa': BRANDS_DF[(BRANDS_DF.category == cat) & (BRANDS_DF.is_tbwa_client)].brand_id.tolist(),
            'competitor': BRANDS_DF[(BRANDS_DF.category == cat) & (~BRANDS_DF.is_tbwa_client)].brand_id.tolist(),
            'all': BRANDS_DF[BRANDS_DF.category == cat].brand_id.tolist()
        }
    return lookups

BRAND_LOOKUPS = build_brand_lookups()

# Special handling for JTI within tobacco
JTI_IDS = BRANDS_DF[(BRANDS_DF.company == 'Japan Tobacco International')].brand_id.tolist()
NON_JTI_TOBACCO_IDS = [bid for bid in BRAND_LOOKUPS['Tobacco']['all'] if bid not in JTI_IDS]

logger.info(f"Loaded {len(BRANDS_DF)} brands, {len(SKU_DF)} SKUs, {len(LOCATIONS_DF)} locations")
logger.info(f"Category distribution: {BRANDS_DF.category.value_counts().to_dict()}")

# MCP Tools
class MCPTools:
    @staticmethod
    async def generate_synthetic_data(request: GenerationRequest) -> Dict[str, Any]:
        """Generate synthetic retail data with realistic market share"""
        try:
            if request.dataset_type == "transactions":
                result = await MCPTools._generate_transactions(request)
            else:
                return {"success": False, "error": f"Dataset type {request.dataset_type} not yet implemented"}
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating synthetic data: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def _generate_transactions(request: GenerationRequest) -> Dict[str, Any]:
        """Generate transaction data with realistic market simulation"""
        start_date = date.fromisoformat(request.start_date) if request.start_date else date(2024, 1, 1)
        end_date = date.fromisoformat(request.end_date) if request.end_date else date(2024, 12, 31)
        
        # Calculate weighted location distribution
        location_weights = []
        for _, loc in LOCATIONS_DF.iterrows():
            region_weight = REGIONAL_WEIGHTS.get(loc.region, 1.0)
            city_weight = CITY_MULTIPLIERS.get(loc.city_or_municipality, CITY_MULTIPLIERS['default'])
            location_weights.append(region_weight * city_weight)
        
        # Normalize weights
        total_weight = sum(location_weights)
        location_weights = [w/total_weight for w in location_weights]
        
        rows = []
        txn_counter = 1
        
        if request.coverage_first:
            # First pass: ensure minimum coverage per region
            MIN_PER_REGION = max(50, request.num_records // (len(REGIONAL_WEIGHTS) * 4))
            
            for region in REGIONAL_WEIGHTS.keys():
                region_locs = LOCATIONS_DF[LOCATIONS_DF.region == region]
                if len(region_locs) > 0:
                    # Generate proportional to region weight
                    region_target = int(MIN_PER_REGION * REGIONAL_WEIGHTS[region])
                    for _ in range(region_target):
                        loc = region_locs.sample(1).iloc[0]
                        txn = await MCPTools._generate_single_transaction(
                            loc, start_date, end_date, txn_counter
                        )
                        rows.append(txn)
                        txn_counter += 1
        
        # Second pass: fill remaining with weighted distribution
        remaining = request.num_records - len(rows)
        for _ in range(remaining):
            # Pick location based on economic weights
            loc_idx = np.random.choice(len(LOCATIONS_DF), p=location_weights)
            loc = LOCATIONS_DF.iloc[loc_idx]
            
            txn = await MCPTools._generate_single_transaction(
                loc, start_date, end_date, txn_counter
            )
            rows.append(txn)
            txn_counter += 1
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Calculate summary statistics
        tbwa_revenue = df[df.is_tbwa_client]['total_amount'].sum()
        total_revenue = df['total_amount'].sum()
        tbwa_share = tbwa_revenue / total_revenue if total_revenue > 0 else 0
        
        tobacco_txns = len(df[df.category == 'Tobacco'])
        tobacco_share = tobacco_txns / len(df) if len(df) > 0 else 0
        
        jti_txns = len(df[df.brand_id.isin(JTI_IDS)])
        jti_tobacco_share = jti_txns / tobacco_txns if tobacco_txns > 0 else 0
        
        # Category breakdown
        category_dist = df.groupby('category').size() / len(df)
        tbwa_by_category = df[df.is_tbwa_client].groupby('category').size() / df.groupby('category').size()
        
        logger.info(f"Generated {len(df)} transactions")
        logger.info(f"TBWA revenue share: {tbwa_share:.1%} (expected ~22%)")
        logger.info(f"Category distribution: {category_dist.to_dict()}")
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transactions_{timestamp}.{request.output_format}"
        output_path = OUTPUT_DIR / filename
        
        if request.output_format == "csv":
            df.to_csv(output_path, index=False)
        elif request.output_format == "json":
            df.to_json(output_path, orient="records", date_format="iso")
        elif request.output_format == "parquet":
            df.to_parquet(output_path, index=False)
        
        return {
            "success": True,
            "records_generated": len(df),
            "output_path": str(output_path),
            "summary": {
                "tbwa_client_share": tbwa_share,
                "tobacco_share": tobacco_share,
                "jti_tobacco_share": jti_tobacco_share,
                "regions_covered": df['region'].nunique(),
                "date_range": f"{df['datetime'].min()} to {df['datetime'].max()}",
                "category_distribution": category_dist.to_dict(),
                "tbwa_by_category": tbwa_by_category.fillna(0).to_dict()
            }
        }
    
    @staticmethod
    async def _generate_single_transaction(loc, start_date, end_date, txn_id):
        """Generate a single transaction with category-based brand selection"""
        # Random datetime with time patterns
        days_range = (end_date - start_date).days
        txn_date = start_date + timedelta(days=random.randint(0, days_range))
        
        # Time patterns: peak hours 6-9am, 5-8pm
        hour_weights = [0.5] * 6 + [1.5] * 3 + [1.0] * 8 + [1.5] * 3 + [0.8] * 4
        hour = np.random.choice(24, p=[w/sum(hour_weights) for w in hour_weights])
        minute = random.randint(0, 59)
        txn_datetime = datetime.combine(txn_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
        
        # Payday surge (15th and 30th)
        if txn_date.day in [15, 30]:
            quantity_multiplier = 1.4
        # Weekend boost
        elif txn_date.weekday() >= 5:
            quantity_multiplier = 1.25
        else:
            quantity_multiplier = 1.0
        
        # Select category based on realistic weights
        category = np.random.choice(
            list(CATEGORY_WEIGHTS.keys()),
            p=list(CATEGORY_WEIGHTS.values())
        )
        
        # Select brand within category based on realistic market share
        tbwa_share = TBWA_CATEGORY_SHARE.get(category, 0)
        
        if category == 'Tobacco':
            # Special handling for tobacco - JTI gets 40%
            if random.random() < 0.40:
                brand_id = random.choice(JTI_IDS) if JTI_IDS else 33
            else:
                brand_id = random.choice(NON_JTI_TOBACCO_IDS) if NON_JTI_TOBACCO_IDS else 99
        else:
            # Normal category selection
            if random.random() < tbwa_share:
                # Select TBWA client brand
                tbwa_brands = BRAND_LOOKUPS[category]['tbwa']
                if tbwa_brands:
                    brand_id = random.choice(tbwa_brands)
                else:
                    # No TBWA brands in this category
                    comp_brands = BRAND_LOOKUPS[category]['competitor']
                    brand_id = random.choice(comp_brands) if comp_brands else 1
            else:
                # Select competitor brand
                comp_brands = BRAND_LOOKUPS[category]['competitor']
                if comp_brands:
                    brand_id = random.choice(comp_brands)
                else:
                    # Fallback to any brand in category
                    all_brands = BRAND_LOOKUPS[category]['all']
                    brand_id = random.choice(all_brands) if all_brands else 1
        
        # Get brand info
        brand_info = BRANDS_DF[BRANDS_DF.brand_id == brand_id].iloc[0]
        
        # Get SKU for brand
        brand_skus = SKU_DF[SKU_DF.brand_id == brand_id]
        if len(brand_skus) > 0:
            # Prefer smaller pack sizes (more common in sari-sari)
            if len(brand_skus) > 1:
                # Sort by pack size and pick from smaller ones
                brand_skus_sorted = brand_skus.sort_values('pack_size')
                # 70% chance to pick from smaller half
                if random.random() < 0.7:
                    sku = brand_skus_sorted.iloc[:len(brand_skus_sorted)//2 + 1].sample(1).iloc[0]
                else:
                    sku = brand_skus_sorted.sample(1).iloc[0]
            else:
                sku = brand_skus.iloc[0]
        else:
            # Fallback to any SKU
            sku = SKU_DF.sample(1).iloc[0]
        
        # Generate quantity (sari-sari stores typically sell small quantities)
        if category == 'Tobacco':
            # Cigarettes often bought by piece or pack
            base_quantity = np.random.choice([1, 2], p=[0.8, 0.2])
        elif category in ['Snacks', 'Beverage', 'CSD']:
            # Snacks and drinks occasionally bought in multiples
            base_quantity = np.random.choice([1, 2, 3], p=[0.7, 0.25, 0.05])
        else:
            # Most other items bought singly
            base_quantity = np.random.choice([1, 2], p=[0.9, 0.1])
        
        quantity = int(base_quantity * quantity_multiplier)
        
        # Apply regional income adjustments to quantity
        region_factor = REGIONAL_WEIGHTS.get(loc.region, 1.0)
        if region_factor < 1.0 and random.random() < 0.3:
            # Lower income regions sometimes buy less
            quantity = max(1, quantity - 1)
        
        # Price with small variance (sari-sari stores have fairly standard pricing)
        unit_price = round(sku.msrp * np.random.uniform(0.98, 1.02), 2)
        
        return {
            'txn_id': f'TXN{txn_id:08d}',
            'datetime': txn_datetime.isoformat(),
            'store_id': hashlib.md5(f"{loc.store_name}{loc.barangay}".encode()).hexdigest()[:8],
            'store_name': loc.store_name,
            'sku_id': sku.sku_id,
            'sku_name': sku.sku_name,
            'brand_id': brand_id,
            'brand_name': brand_info.brand_name,
            'company': brand_info.company,
            'category': brand_info.category,
            'quantity': quantity,
            'unit_price': unit_price,
            'total_amount': round(quantity * unit_price, 2),
            'barangay': loc.barangay,
            'city': loc.city_or_municipality,
            'province': loc.province,
            'region': loc.region,
            'is_tbwa_client': brand_info.is_tbwa_client
        }
    
    @staticmethod
    async def validate_data_quality(request: DataQualityRequest) -> Dict[str, Any]:
        """Validate generated data quality"""
        try:
            df = pd.read_csv(request.dataset_path)
            
            results = {
                "total_records": len(df),
                "validation_results": {}
            }
            
            if "completeness" in request.validation_rules:
                null_counts = df.isnull().sum()
                total_cells = len(df) * len(df.columns)
                completeness_score = 1 - (null_counts.sum() / total_cells)
                results["validation_results"]["completeness"] = {
                    "completeness_score": completeness_score,
                    "null_counts": null_counts.to_dict()
                }
            
            if "distribution" in request.validation_rules:
                # Check TBWA share
                tbwa_revenue = df[df.is_tbwa_client]['total_amount'].sum()
                total_revenue = df['total_amount'].sum()
                tbwa_share = tbwa_revenue / total_revenue
                
                # Check category distribution
                category_dist = df.groupby('category').size() / len(df)
                
                # Check tobacco share
                tobacco_txns = len(df[df.category == 'Tobacco'])
                tobacco_share = tobacco_txns / len(df)
                
                # Check JTI share within tobacco
                if tobacco_txns > 0:
                    jti_txns = len(df[df.brand_id.isin(JTI_IDS)])
                    jti_tobacco_share = jti_txns / tobacco_txns
                else:
                    jti_tobacco_share = 0
                
                # Regional coverage
                regions_covered = df['region'].nunique()
                
                results["validation_results"]["distribution"] = {
                    "tbwa_share": tbwa_share,
                    "expected_tbwa_share": EXPECTED_TBWA_SHARE,
                    "tobacco_share": tobacco_share,
                    "jti_tobacco_share": jti_tobacco_share,
                    "regions_covered": regions_covered,
                    "total_regions": len(REGIONAL_WEIGHTS),
                    "category_distribution": category_dist.to_dict()
                }
            
            if "outliers" in request.validation_rules:
                # Check for price outliers
                q1 = df['unit_price'].quantile(0.25)
                q3 = df['unit_price'].quantile(0.75)
                iqr = q3 - q1
                outliers = df[(df['unit_price'] < q1 - 1.5 * iqr) | (df['unit_price'] > q3 + 1.5 * iqr)]
                
                results["validation_results"]["outliers"] = {
                    "outlier_count": len(outliers),
                    "outlier_percentage": len(outliers) / len(df),
                    "price_range": {
                        "min": df['unit_price'].min(),
                        "max": df['unit_price'].max(),
                        "mean": df['unit_price'].mean(),
                        "median": df['unit_price'].median()
                    }
                }
            
            results["success"] = True
            return results
            
        except Exception as e:
            logger.error(f"Error validating data: {e}")
            return {"success": False, "error": str(e)}

# API Endpoints
@app.get("/")
async def root():
    return {
        "service": "Synthetic Data Generator MCP Server V3",
        "version": "3.0.0", 
        "status": "running",
        "features": [
            "Realistic market share (~22% TBWA)",
            "177 brands across all major players",
            "1200+ authentic SKUs with sari-sari pack sizes",
            "Category distribution matching actual stores",
            "Economic weighting by region/city"
        ],
        "endpoints": [
            "/health",
            "/mcp/tools/generate_data",
            "/mcp/tools/validate_quality"
        ]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "data_loaded": {
            "brands": len(BRANDS_DF),
            "skus": len(SKU_DF),
            "locations": len(LOCATIONS_DF)
        },
        "expected_tbwa_share": f"{EXPECTED_TBWA_SHARE:.1%}"
    }

@app.post("/mcp/tools/generate_data")
async def generate_data(request: GenerationRequest):
    """Generate synthetic data endpoint"""
    return await MCPTools.generate_synthetic_data(request)

@app.post("/mcp/tools/validate_quality")
async def validate_quality(request: DataQualityRequest):
    """Validate data quality endpoint"""
    return await MCPTools.validate_data_quality(request)

if __name__ == "__main__":
    logger.info("Starting Synthetic Data Generator MCP Server V3...")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Loaded {len(BRANDS_DF)} brands, {len(SKU_DF)} SKUs, {len(LOCATIONS_DF)} locations")
    logger.info(f"Expected TBWA market share: {EXPECTED_TBWA_SHARE:.1%}")
    logger.info("Server running at http://localhost:8005")
    
    uvicorn.run(app, host="0.0.0.0", port=8005)