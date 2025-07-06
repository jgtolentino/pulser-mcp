#!/usr/bin/env python3
"""
Synthetic Data Generator MCP Server V2 - PH Retail dataset expansion
Generates realistic retail transaction data with accurate TBWA client footprint
Based on economic weighting and accurate market share distribution
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
app = FastAPI(title="Synthetic Data Generator MCP Server V2")

# Data directories
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Category weights based on share sheet
CATEGORY_WEIGHTS = {
    'Dairy': 0.13,          # Alaska dominates (90%)
    'Coffee Creamer': 0.02, # Alaska Krem-Top
    'Snacks': 0.15,         # Oishi dominates (85%)
    'Beverage': 0.10,       # Del Monte + competitors
    'Condiment': 0.03,      # Del Monte sauces
    'Canned': 0.02,         # Del Monte fruits
    'Home Care': 0.10,      # Peerless Champion etc (80%)
    'Personal Care': 0.06,  # Peerless Hana, Care Plus
    'Tobacco': 0.18,        # JTI 40% share
    'Food': 0.04,           # Various
    'Other': 0.17           # Competitor-only bucket
}

# TBWA client dominance within each category
TBWA_CATEGORY_DOMINANCE = {
    'Dairy': 0.90,          # Alaska 90% of dairy
    'Coffee Creamer': 0.95, # Alaska dominates
    'Snacks': 0.85,         # Oishi 85% of snacks  
    'Beverage': 0.40,       # Del Monte partial (vs Coke, Pepsi)
    'Condiment': 0.85,      # Del Monte dominates sauces
    'Canned': 0.90,         # Del Monte fruits
    'Home Care': 0.80,      # Peerless 80% share
    'Personal Care': 0.75,  # Peerless strong position
    'Tobacco': 0.40,        # JTI 40% of tobacco
    'Food': 0.20,           # Mixed competition
    'Other': 0.0            # No TBWA presence
}

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

# Company to category mapping for brand selection
COMPANY_CATEGORY_MAP = {
    'Alaska Milk Corporation': ['Dairy', 'Coffee Creamer'],
    'Liwayway Marketing Corporation': ['Snacks', 'Beverage'],
    'Peerless Products Manufacturing': ['Home Care', 'Personal Care'],
    'Del Monte Philippines': ['Beverage', 'Condiment', 'Canned', 'Food'],
    'Japan Tobacco International': ['Tobacco']
}

# Pydantic models
class GenerationRequest(BaseModel):
    dataset_type: str = "transactions"  # transactions, inventory, customer_profiles
    num_records: int = 17000
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    output_format: str = "csv"  # csv, json, parquet
    coverage_first: bool = True  # Ensure all regions have data

class DataQualityRequest(BaseModel):
    dataset_path: str
    validation_rules: Optional[List[str]] = ["completeness", "distribution", "outliers"]

class MarketSimulationRequest(BaseModel):
    scenario: str  # normal, peak_season, competitor_promo, supply_shortage
    duration_days: int = 30
    affected_brands: Optional[List[str]] = []
    impact_factor: float = 1.2

# Load master data
def load_master_data():
    """Load brand, product, and location data"""
    try:
        # Load from CSV files if they exist
        brands_path = DATA_DIR / "brands.csv"
        sku_path = DATA_DIR / "sku_catalog.csv"
        locations_path = DATA_DIR / "locations_master.csv"
        
        if brands_path.exists() and sku_path.exists() and locations_path.exists():
            brands_df = pd.read_csv(brands_path)
            sku_df = pd.read_csv(sku_path)
            locations_df = pd.read_csv(locations_path)
        else:
            # Fallback to embedded data
            logger.warning("Master data files not found, using embedded data")
            brands_df, sku_df, locations_df = create_embedded_master_data()
            
        return brands_df, sku_df, locations_df
        
    except Exception as e:
        logger.error(f"Error loading master data: {e}")
        raise

def create_embedded_master_data():
    """Create master data if CSV files don't exist"""
    # Create brands DataFrame
    brands_data = []
    brand_id = 1
    
    # Alaska Milk Corporation (6 brands)
    for name in ['Alaska Evaporated Milk', 'Alaska Condensed Milk', 'Alaska Powdered Milk',
                 'Krem-Top', 'Alpine', 'Cow Bell']:
        cat = 'Coffee Creamer' if name == 'Krem-Top' else 'Dairy'
        brands_data.append({
            'brand_id': brand_id,
            'brand_name': name,
            'company': 'Alaska Milk Corporation',
            'is_tbwa_client': True,
            'category': cat
        })
        brand_id += 1
    
    # Continue with other companies...
    # (Abbreviated for space - full implementation would include all 57 brands)
    
    brands_df = pd.DataFrame(brands_data)
    
    # Create SKU catalog
    sku_df = pd.DataFrame([
        {'sku_id': 1000, 'brand_id': 1, 'sku_name': 'Alaska Evap 370ml', 'pack_size': 370, 'unit': 'ml', 'msrp': 59},
        # ... more SKUs
    ])
    
    # Create locations
    locations_df = pd.DataFrame([
        {
            'region': 'NCR',
            'province': 'Metro Manila', 
            'city_or_municipality': 'Manila',
            'barangay': 'Tondo',
            'store_name': "Aling Rosa's Sari-Sari Store"
        },
        # ... more locations
    ])
    
    return brands_df, sku_df, locations_df

# Initialize master data
BRANDS_DF, SKU_DF, LOCATIONS_DF = load_master_data()

# Extract brand categories
BRANDS_BY_CATEGORY = {}
for cat in CATEGORY_WEIGHTS.keys():
    if cat != 'Other':
        BRANDS_BY_CATEGORY[cat] = {
            'tbwa': BRANDS_DF[(BRANDS_DF.category == cat) & (BRANDS_DF.is_tbwa_client)].brand_id.tolist(),
            'competitor': BRANDS_DF[(BRANDS_DF.category == cat) & (~BRANDS_DF.is_tbwa_client)].brand_id.tolist()
        }

# Special handling for tobacco
JTI_IDS = BRANDS_DF[(BRANDS_DF.company == 'Japan Tobacco International')].brand_id.tolist()
NON_JTI_TOBACCO_IDS = BRANDS_DF[(BRANDS_DF.category == 'Tobacco') & 
                                 (BRANDS_DF.company != 'Japan Tobacco International')].brand_id.tolist()

# MCP Tools
class MCPTools:
    @staticmethod
    async def generate_synthetic_data(request: GenerationRequest) -> Dict[str, Any]:
        """Generate synthetic retail data with economic weighting"""
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
                "date_range": f"{df['datetime'].min()} to {df['datetime'].max()}"
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
        
        # Select category based on weights
        category = np.random.choice(
            list(CATEGORY_WEIGHTS.keys()),
            p=list(CATEGORY_WEIGHTS.values())
        )
        
        # Select brand within category
        if category == 'Other':
            # Always competitor brands for 'Other' category
            available_brands = BRANDS_DF[
                (~BRANDS_DF.is_tbwa_client) & 
                (~BRANDS_DF.category.isin(['Tobacco']))
            ]
            brand_id = available_brands.sample(1).iloc[0].brand_id if len(available_brands) > 0 else 1
        
        elif category == 'Tobacco':
            # Special handling for tobacco - JTI gets 40%
            if random.random() < TBWA_CATEGORY_DOMINANCE['Tobacco']:
                brand_id = random.choice(JTI_IDS)
            else:
                brand_id = random.choice(NON_JTI_TOBACCO_IDS) if NON_JTI_TOBACCO_IDS else JTI_IDS[0]
        
        else:
            # Check TBWA dominance for this category
            dominance = TBWA_CATEGORY_DOMINANCE.get(category, 0.5)
            
            if random.random() < dominance:
                # Select TBWA client brand
                tbwa_brands = BRANDS_BY_CATEGORY.get(category, {}).get('tbwa', [])
                if tbwa_brands:
                    brand_id = random.choice(tbwa_brands)
                else:
                    # Fallback to any TBWA brand
                    brand_id = BRANDS_DF[BRANDS_DF.is_tbwa_client].sample(1).iloc[0].brand_id
            else:
                # Select competitor brand
                comp_brands = BRANDS_BY_CATEGORY.get(category, {}).get('competitor', [])
                if comp_brands:
                    brand_id = random.choice(comp_brands)
                else:
                    # Fallback to any competitor brand
                    brand_id = BRANDS_DF[~BRANDS_DF.is_tbwa_client].sample(1).iloc[0].brand_id
        
        # Get brand info
        brand_info = BRANDS_DF[BRANDS_DF.brand_id == brand_id].iloc[0]
        
        # Get SKU for brand
        brand_skus = SKU_DF[SKU_DF.brand_id == brand_id]
        if len(brand_skus) > 0:
            sku = brand_skus.sample(1).iloc[0]
        else:
            # Fallback to any SKU
            sku = SKU_DF.sample(1).iloc[0]
        
        # Generate quantity (affected by time patterns)
        base_quantity = np.random.choice([1, 2, 3, 4], p=[0.6, 0.25, 0.10, 0.05])
        quantity = int(base_quantity * quantity_multiplier)
        
        # Apply regional income adjustments to quantity
        region_factor = REGIONAL_WEIGHTS.get(loc.region, 1.0)
        if region_factor < 1.0 and random.random() < 0.3:
            # Lower income regions sometimes buy less
            quantity = max(1, quantity - 1)
        
        # Price with variance
        unit_price = round(sku.msrp * np.random.uniform(0.95, 1.05), 2)
        
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
                
                # Check tobacco share
                tobacco_txns = len(df[df.category == 'Tobacco'])
                tobacco_share = tobacco_txns / len(df)
                
                # Check JTI share within tobacco
                jti_txns = len(df[df.brand_id.isin(JTI_IDS)])
                jti_tobacco_share = jti_txns / tobacco_txns if tobacco_txns > 0 else 0
                
                # Regional coverage
                regions_covered = df['region'].nunique()
                
                results["validation_results"]["distribution"] = {
                    "tbwa_share": tbwa_share,
                    "tobacco_share": tobacco_share,
                    "jti_tobacco_share": jti_tobacco_share,
                    "regions_covered": regions_covered,
                    "total_regions": len(REGIONAL_WEIGHTS)
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
                        "mean": df['unit_price'].mean()
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
        "service": "Synthetic Data Generator MCP Server V2",
        "version": "2.0.0",
        "status": "running",
        "endpoints": [
            "/health",
            "/mcp/tools/generate_data",
            "/mcp/tools/validate_quality"
        ]
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/mcp/tools/generate_data")
async def generate_data(request: GenerationRequest):
    """Generate synthetic data endpoint"""
    return await MCPTools.generate_synthetic_data(request)

@app.post("/mcp/tools/validate_quality")
async def validate_quality(request: DataQualityRequest):
    """Validate data quality endpoint"""
    return await MCPTools.validate_data_quality(request)

if __name__ == "__main__":
    logger.info("Starting Synthetic Data Generator MCP Server V2...")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Loaded {len(BRANDS_DF)} brands, {len(SKU_DF)} SKUs, {len(LOCATIONS_DF)} locations")
    logger.info("Server running at http://localhost:8005")
    
    uvicorn.run(app, host="0.0.0.0", port=8005)