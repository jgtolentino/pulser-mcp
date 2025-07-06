#!/usr/bin/env python3
"""
Synthetic Data Generator MCP Server - PH Retail dataset expansion
Generates realistic retail transaction data with TBWA client footprint
NOTE: This is the original version. For accurate market share distribution,
use synthetic_server_v2.py which implements the correct category weights.
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, date
import logging
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
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

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os

# JWT Configuration
SECRET_KEY = os.getenv("PULSER_JWT_SECRET", "change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = ["/", "/health", "/auth/token"]

app = FastAPI(title="Synthetic Data Generator MCP Server (Original)")

from fastapi import APIRouter

# Create versioned router
api_v1 = APIRouter(prefix="/api/v1")

# IMPORTANT: This server uses simplified market share logic.
# For production use, please use synthetic_server_v2.py which implements:
# - Accurate category-based market share (55% TBWA total)
# - Economic weighting by region and city
# - Coverage-first generation ensuring all regions are represented

# Data directories
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Pydantic models
class GenerationRequest(BaseModel):
    dataset_type: str = "transactions"  # transactions, inventory, customer_profiles
    num_records: int = 10000
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    client_weight: float = 0.55  # TBWA client share
    tobacco_share: float = 0.18  # Tobacco transaction share
    output_format: str = "csv"  # csv, json, parquet

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
        # Brands data
        brands_df = pd.DataFrame({
            'brand_id': range(1, 58),
            'brand_name': [
                # Alaska Milk Corporation (1-6)
                'Alaska Evaporated Milk', 'Alaska Condensed Milk', 'Alaska Powdered Milk',
                'Krem-Top', 'Alpine', 'Cow Bell',
                
                # Oishi/Liwayway (7-18)
                'Oishi Prawn Crackers', 'Oishi Pillows', "Oishi Marty's", 'Oishi Ridges',
                'Oishi Bread Pan', 'Oishi Gourmet Picks', 'Oishi Crispy Patata', 'Oishi Smart C+',
                'Oaties', 'Hi-Ho', 'Rinbee', 'Deli Mex',
                
                # Peerless Products (19-24)
                'Champion', 'Calla', 'Hana', 'Cyclone', 'Pride', 'Care Plus',
                
                # Del Monte (25-32)
                'Del Monte Pineapple', 'Del Monte Tomato', 'Del Monte Spaghetti Sauce',
                'Del Monte Fruit Cocktail', 'Del Monte Pasta', 'S&W', "Today's", "Fit 'n Right",
                
                # JTI Tobacco (33-39)
                'Winston', 'Camel', 'Mevius', 'LD', 'Mighty', 'Caster', 'Glamour',
                
                # Competitors (40-57)
                'Nestlé Bear Brand', 'Milo', 'Nescafé', 'Maggi',
                'Surf', 'Breeze', 'Ariel', 'Tide', 'Downy',
                'Coca-Cola', 'Sprite', 'Royal', 'Pepsi', 'Mountain Dew',
                'Marlboro', 'Fortune', 'Hope', 'Champion Filter'
            ],
            'company': [
                # TBWA Clients
                'Alaska Milk Corporation'] * 6 +
                ['Liwayway Marketing Corporation'] * 12 +
                ['Peerless Products Manufacturing'] * 6 +
                ['Del Monte Philippines'] * 8 +
                ['Japan Tobacco International'] * 7 +
                # Competitors
                ['Nestlé'] * 4 +
                ['Unilever'] * 2 +
                ['P&G'] * 3 +
                ['Coca-Cola'] * 3 +
                ['PepsiCo'] * 2 +
                ['PMFTC'] * 3 +
                ['Kentucky Trading'],
            'is_tbwa_client': [True] * 39 + [False] * 18,
            'category': (
                ['Dairy'] * 6 +
                ['Snacks'] * 13 + ['Beverage'] * 2 + ['Snacks'] * 3 +
                ['Home Care'] * 4 + ['Personal Care'] * 2 +
                ['Beverage'] * 2 + ['Condiment'] * 3 + ['Canned'] * 2 + ['Beverage'] +
                ['Tobacco'] * 7 +
                ['Dairy'] + ['Beverage'] * 3 +
                ['Home Care'] * 5 +
                ['Beverage'] * 5 +
                ['Tobacco'] * 4
            )
        })
        
        # SKU catalog with realistic prices
        sku_data = []
        sku_id = 1000
        
        # Generate SKUs for each brand
        sku_configs = {
            # Alaska Milk
            1: [('140ml', 140, 'ml', 25), ('154ml', 154, 'ml', 30), ('370ml', 370, 'ml', 59)],
            2: [('300ml', 300, 'ml', 62), ('390ml', 390, 'ml', 75)],
            3: [('33g', 33, 'g', 17), ('80g', 80, 'g', 35), ('150g', 150, 'g', 65)],
            4: [('170g', 170, 'g', 52), ('250g', 250, 'g', 78)],
            
            # Oishi
            7: [('30g', 30, 'g', 10), ('90g', 90, 'g', 29), ('150g', 150, 'g', 45)],
            8: [('96g', 96, 'g', 38), ('150g', 150, 'g', 55)],
            
            # JTI Tobacco
            33: [('20s', 20, 'sticks', 140), ('10s', 10, 'sticks', 75)],
            34: [('20s', 20, 'sticks', 150), ('10s', 10, 'sticks', 80)],
            35: [('20s', 20, 'sticks', 155), ('10s', 10, 'sticks', 82)],
            
            # Competitors
            40: [('150g', 150, 'g', 85), ('300g', 300, 'g', 165)],
            49: [('330ml', 330, 'ml', 20), ('1.5L', 1500, 'ml', 65)],
        }
        
        for brand_id in range(1, 58):
            configs = sku_configs.get(brand_id, [('standard', 100, 'g', 50)])
            for size_name, size_val, unit, price in configs:
                sku_data.append({
                    'sku_id': sku_id,
                    'brand_id': brand_id,
                    'sku_name': f"{brands_df[brands_df.brand_id == brand_id].brand_name.iloc[0]} {size_name}",
                    'pack_size': size_val,
                    'unit': unit,
                    'msrp': price
                })
                sku_id += 1
        
        sku_df = pd.DataFrame(sku_data)
        
        # Locations with authentic Filipino sari-sari store names
        locations_data = []
        
        location_configs = {
            'NCR': {
                'Metro Manila': {
                    'Manila': ['Tondo', 'Quiapo', 'San Andres', 'Sampaloc', 'Santa Cruz'],
                    'Quezon City': ['Commonwealth', 'Novaliches', 'Fairview', 'Diliman', 'Cubao'],
                    'Caloocan': ['Grace Park', 'Camarin', 'Bagong Silang', 'Deparo', 'Sangandaan'],
                    'Makati': ['Poblacion', 'Guadalupe', 'Cembo', 'Pembo', 'Bangkal'],
                    'Pasig': ['Ortigas', 'Ugong', 'Rosario', 'Santolan', 'Manggahan']
                }
            },
            'Region III': {
                'Pampanga': {
                    'Angeles City': ['Balibago', 'Pampang', 'Amsic', 'Mining', 'Santo Domingo'],
                    'San Fernando': ['Del Pilar', 'Bulaon', 'Malino', 'Juliana', 'Lara']
                },
                'Bulacan': {
                    'Malolos': ['Tikay', 'Lugam', 'Balite', 'Longos', 'Dakila'],
                    'Meycauayan': ['Banga', 'Perez', 'Malhacan', 'Saluysoy', 'Langka']
                }
            },
            'Region IV-A': {
                'Laguna': {
                    'Biñan': ['Santo Niño', 'Zapote', 'Langkiwa', 'Malaban', 'Ganado'],
                    'Santa Rosa': ['Tagapo', 'Dita', 'Balibago', 'Kanluran', 'Market Area']
                },
                'Cavite': {
                    'Cavite City': ['San Roque', 'Caridad', 'P. Burgos', 'San Antonio', 'Dalahican'],
                    'Tagaytay': ['Kaybagal', 'Mendez Crossing', 'Tolentino', 'Zambal', 'Patutong Malaki']
                }
            },
            'Region VII': {
                'Cebu': {
                    'Cebu City': ['Lahug', 'IT Park', 'Banilad', 'Talamban', 'Guadalupe'],
                    'Mandaue City': ['Tipolo', 'Guizo', 'Subangdaku', 'Cabancalan', 'Mantuyong'],
                    'Lapu-Lapu City': ['Basak', 'Mactan', 'Agus', 'Maribago', 'Bankal']
                }
            },
            'Region XI': {
                'Davao del Sur': {
                    'Davao City': ['Bangkal', 'Sasa', 'Toril', 'Calinan', 'Bunawan'],
                    'Tagum City': ['Magugpo', 'Madaum', 'Canocotan', 'Pagsabangan', 'Pandapan']
                }
            }
        }
        
        store_name_patterns = [
            "Aling {}'s Store", "Mang {}'s Sari-Sari", "{} Mini Mart",
            "{} Variety Store", "Ka {}'s Tindahan", "{} General Merchandise",
            "{} Daily Needs", "{} Neighborhood Store", "{} Family Mart",
            "{} Stop & Shop", "{} Quick Mart", "{} One Stop Shop"
        ]
        
        filipino_names = [
            'Rosa', 'Maria', 'Teresa', 'Gloria', 'Nena', 'Linda', 'Susan', 'Helen',
            'Pedro', 'Juan', 'Roberto', 'Ricardo', 'Domingo', 'Eduardo', 'Bert',
            'Lorna', 'Josie', 'Betty', 'Carmen', 'Erlinda', 'Zenaida',
            'Ruben', 'Danny', 'Lito', 'Romy', 'Nanding', 'Boy', 'Jun'
        ]
        
        for region, provinces in location_configs.items():
            for province, cities in provinces.items():
                for city, barangays in cities.items():
                    for barangay in barangays:
                        # Generate 2-3 stores per barangay
                        for _ in range(random.randint(2, 3)):
                            pattern = random.choice(store_name_patterns)
                            name = random.choice(filipino_names)
                            store_name = pattern.format(name)
                            
                            locations_data.append({
                                'region': region,
                                'province': province,
                                'city_or_municipality': city,
                                'barangay': barangay,
                                'store_name': store_name
                            })
        
        locations_df = pd.DataFrame(locations_data)
        
        return brands_df, sku_df, locations_df
        
    except Exception as e:
        logger.error(f"Error loading master data: {e}")
        raise

# Initialize master data
BRANDS_DF, SKU_DF, LOCATIONS_DF = load_master_data()

# Extract brand categories
CLIENT_BRAND_IDS = BRANDS_DF[BRANDS_DF.is_tbwa_client].brand_id.tolist()
COMP_BRAND_IDS = BRANDS_DF[~BRANDS_DF.is_tbwa_client].brand_id.tolist()
TOBACCO_IDS = BRANDS_DF[BRANDS_DF.category == 'Tobacco'].brand_id.tolist()
JTI_IDS = BRANDS_DF[(BRANDS_DF.company == 'Japan Tobacco International') & 
                    (BRANDS_DF.category == 'Tobacco')].brand_id.tolist()
NON_JTI_IDS = list(set(TOBACCO_IDS) - set(JTI_IDS))

# MCP Tools
class MCPTools:
    @staticmethod
    async def generate_synthetic_data(request: GenerationRequest) -> Dict[str, Any]:
        """Generate synthetic retail data"""
        try:
            if request.dataset_type == "transactions":
                result = await MCPTools._generate_transactions(request)
            elif request.dataset_type == "inventory":
                result = await MCPTools._generate_inventory(request)
            elif request.dataset_type == "customer_profiles":
                result = await MCPTools._generate_customers(request)
            else:
                return {"success": False, "error": f"Unknown dataset type: {request.dataset_type}"}
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating synthetic data: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def _generate_transactions(request: GenerationRequest) -> Dict[str, Any]:
        """Generate transaction data with realistic market simulation"""
        start_date = date.fromisoformat(request.start_date) if request.start_date else date(2024, 1, 1)
        end_date = date.fromisoformat(request.end_date) if request.end_date else date(2024, 12, 31)
        
        rows = []
        tobacco_txn_pct = request.tobacco_share
        jti_share = 0.40  # JTI's share within tobacco
        
        for i in range(request.num_records):
            # Pick location
            loc = LOCATIONS_DF.sample(1).iloc[0]
            
            # Pick brand based on market share
            if random.random() < tobacco_txn_pct:
                # Tobacco transaction
                if random.random() < jti_share:
                    brand_id = random.choice(JTI_IDS)
                else:
                    brand_id = random.choice(NON_JTI_IDS)
            else:
                # FMCG transaction
                if random.random() < request.client_weight:
                    brand_id = random.choice(CLIENT_BRAND_IDS)
                else:
                    brand_id = random.choice(COMP_BRAND_IDS)
            
            # Get SKU for brand
            brand_skus = SKU_DF[SKU_DF.brand_id == brand_id]
            if brand_skus.empty:
                continue
            sku = brand_skus.sample(1).iloc[0]
            
            # Generate transaction details
            qty = np.random.choice([1, 2, 3, 4, 5, 6], p=[0.5, 0.25, 0.12, 0.08, 0.03, 0.02])
            
            # Price with ±10% variance from MSRP
            unit_price = round(sku.msrp * np.random.uniform(0.9, 1.1), 2)
            
            # Time patterns - more sales in evening
            hour = np.random.choice(range(6, 22), p=[0.02, 0.03, 0.05, 0.06, 0.07, 0.08, 
                                                      0.09, 0.10, 0.10, 0.09, 0.08, 0.07,
                                                      0.06, 0.05, 0.03, 0.02])
            
            txn_date = fake.date_between(start_date, end_date)
            txn_datetime = datetime.combine(txn_date, datetime.min.time()) + timedelta(hours=hour)
            
            row = {
                'txn_id': str(uuid.uuid4()),
                'datetime': txn_datetime.isoformat(),
                'store_id': f"{loc.city_or_municipality[:3].upper()}-{random.randint(1000, 9999)}",
                'store_name': loc.store_name,
                'sku_id': sku.sku_id,
                'sku_name': sku.sku_name,
                'brand_id': brand_id,
                'brand_name': BRANDS_DF[BRANDS_DF.brand_id == brand_id].brand_name.iloc[0],
                'category': BRANDS_DF[BRANDS_DF.brand_id == brand_id].category.iloc[0],
                'quantity': qty,
                'unit_price': unit_price,
                'total_amount': round(qty * unit_price, 2),
                'barangay': loc.barangay,
                'city': loc.city_or_municipality,
                'province': loc.province,
                'region': loc.region,
                'is_tbwa_client': BRANDS_DF[BRANDS_DF.brand_id == brand_id].is_tbwa_client.iloc[0]
            }
            rows.append(row)
            
            # 6% chance of multi-item basket for tobacco
            if brand_id in TOBACCO_IDS and random.random() < 0.06:
                # Add an FMCG item
                fmcg_brand = random.choice([b for b in CLIENT_BRAND_IDS + COMP_BRAND_IDS 
                                          if b not in TOBACCO_IDS])
                fmcg_skus = SKU_DF[SKU_DF.brand_id == fmcg_brand]
                if not fmcg_skus.empty:
                    fmcg_sku = fmcg_skus.sample(1).iloc[0]
                    fmcg_qty = np.random.choice([1, 2], p=[0.7, 0.3])
                    fmcg_price = round(fmcg_sku.msrp * np.random.uniform(0.9, 1.1), 2)
                    
                    fmcg_row = row.copy()
                    fmcg_row.update({
                        'sku_id': fmcg_sku.sku_id,
                        'sku_name': fmcg_sku.sku_name,
                        'brand_id': fmcg_brand,
                        'brand_name': BRANDS_DF[BRANDS_DF.brand_id == fmcg_brand].brand_name.iloc[0],
                        'category': BRANDS_DF[BRANDS_DF.brand_id == fmcg_brand].category.iloc[0],
                        'quantity': fmcg_qty,
                        'unit_price': fmcg_price,
                        'total_amount': round(fmcg_qty * fmcg_price, 2),
                        'is_tbwa_client': BRANDS_DF[BRANDS_DF.brand_id == fmcg_brand].is_tbwa_client.iloc[0]
                    })
                    rows.append(fmcg_row)
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if request.output_format == "csv":
            output_path = OUTPUT_DIR / f"transactions_{timestamp}.csv"
            df.to_csv(output_path, index=False)
        elif request.output_format == "json":
            output_path = OUTPUT_DIR / f"transactions_{timestamp}.json"
            df.to_json(output_path, orient='records', indent=2)
        else:
            output_path = OUTPUT_DIR / f"transactions_{timestamp}.parquet"
            df.to_parquet(output_path)
        
        # Calculate summary statistics
        summary = {
            "total_transactions": len(df),
            "unique_stores": df.store_id.nunique(),
            "unique_skus": df.sku_id.nunique(),
            "total_revenue": float(df.total_amount.sum()),
            "avg_basket_size": float(df.groupby(['txn_id', 'datetime']).size().mean()),
            "tbwa_client_share": float(df[df.is_tbwa_client].total_amount.sum() / df.total_amount.sum()),
            "tobacco_share": float(df[df.category == 'Tobacco'].total_amount.sum() / df.total_amount.sum()),
            "top_brands": df.groupby('brand_name')['total_amount'].sum().nlargest(10).to_dict(),
            "regional_distribution": df.groupby('region')['total_amount'].sum().to_dict()
        }
        
        return {
            "success": True,
            "dataset_type": "transactions",
            "records_generated": len(df),
            "output_path": str(output_path),
            "file_size_mb": round(output_path.stat().st_size / 1024 / 1024, 2),
            "summary": summary
        }
    
    @staticmethod
    async def validate_data_quality(request: DataQualityRequest) -> Dict[str, Any]:
        """Validate synthetic data quality"""
        try:
            # Load dataset
            file_path = Path(request.dataset_path)
            if not file_path.exists():
                return {"success": False, "error": "File not found"}
            
            if file_path.suffix == '.csv':
                df = pd.read_csv(file_path)
            elif file_path.suffix == '.json':
                df = pd.read_json(file_path)
            elif file_path.suffix == '.parquet':
                df = pd.read_parquet(file_path)
            else:
                return {"success": False, "error": "Unsupported file format"}
            
            validation_results = {}
            
            # Completeness check
            if "completeness" in request.validation_rules:
                null_counts = df.isnull().sum()
                validation_results["completeness"] = {
                    "total_nulls": int(null_counts.sum()),
                    "null_by_column": null_counts.to_dict(),
                    "completeness_score": float(1 - (null_counts.sum() / (len(df) * len(df.columns))))
                }
            
            # Distribution check
            if "distribution" in request.validation_rules and 'brand_name' in df.columns:
                brand_dist = df.groupby('brand_name').size() / len(df)
                validation_results["distribution"] = {
                    "brand_distribution": brand_dist.to_dict(),
                    "category_distribution": df.groupby('category').size().to_dict() if 'category' in df else {},
                    "regional_distribution": df.groupby('region').size().to_dict() if 'region' in df else {}
                }
            
            # Outlier detection
            if "outliers" in request.validation_rules and 'total_amount' in df.columns:
                q1 = df['total_amount'].quantile(0.25)
                q3 = df['total_amount'].quantile(0.75)
                iqr = q3 - q1
                outliers = df[(df['total_amount'] < q1 - 1.5 * iqr) | 
                             (df['total_amount'] > q3 + 1.5 * iqr)]
                
                validation_results["outliers"] = {
                    "outlier_count": len(outliers),
                    "outlier_percentage": float(len(outliers) / len(df) * 100),
                    "outlier_examples": outliers.head(5).to_dict('records')
                }
            
            return {
                "success": True,
                "file_path": str(file_path),
                "total_records": len(df),
                "columns": list(df.columns),
                "validation_results": validation_results
            }
            
        except Exception as e:
            logger.error(f"Error validating data quality: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def simulate_market_scenario(request: MarketSimulationRequest) -> Dict[str, Any]:
        """Simulate market scenarios for testing"""
        try:
            base_params = GenerationRequest(
                dataset_type="transactions",
                num_records=1000 * request.duration_days,
                client_weight=0.55,
                tobacco_share=0.18
            )
            
            # Adjust parameters based on scenario
            if request.scenario == "peak_season":
                # Christmas/New Year peak
                base_params.num_records = int(base_params.num_records * request.impact_factor)
                
            elif request.scenario == "competitor_promo":
                # Reduce TBWA client share
                base_params.client_weight = 0.45
                
            elif request.scenario == "supply_shortage":
                # Reduce availability of affected brands
                base_params.num_records = int(base_params.num_records * 0.7)
            
            # Generate data with scenario adjustments
            result = await MCPTools._generate_transactions(base_params)
            
            if result["success"]:
                result["scenario"] = {
                    "type": request.scenario,
                    "duration_days": request.duration_days,
                    "impact_factor": request.impact_factor,
                    "affected_brands": request.affected_brands
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error simulating market scenario: {e}")
            return {"success": False, "error": str(e)}

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Synthetic Data Generator MCP Server started")
    logger.info(f"Loaded {len(BRANDS_DF)} brands, {len(SKU_DF)} SKUs, {len(LOCATIONS_DF)} store locations")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "active",
        "service": "Synthetic Data Generator MCP Server",
        "data_stats": {
            "brands": len(BRANDS_DF),
            "skus": len(SKU_DF),
            "locations": len(LOCATIONS_DF),
            "tbwa_clients": len(CLIENT_BRAND_IDS),
            "competitors": len(COMP_BRAND_IDS)
        }
    }

@api_v1.post("/mcp/tools/generate_data")
async def generate_data(request: GenerationRequest, current_user: str = Depends(verify_token)):
    """Generate synthetic data"""
    result = await MCPTools.generate_synthetic_data(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/validate_quality")
async def validate_quality(request: DataQualityRequest, current_user: str = Depends(verify_token)):
    """Validate data quality"""
    result = await MCPTools.validate_data_quality(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/simulate_scenario")
async def simulate_scenario(request: MarketSimulationRequest, current_user: str = Depends(verify_token)):
    """Simulate market scenario"""
    result = await MCPTools.simulate_market_scenario(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.get("/mcp/tools/list_outputs")
async def list_outputs(current_user: str = Depends(verify_token)):
    """List generated datasets"""
    outputs = []
    for file in OUTPUT_DIR.glob("*"):
        if file.is_file():
            outputs.append({
                "filename": file.name,
                "size_mb": round(file.stat().st_size / 1024 / 1024, 2),
                "created": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                "type": file.suffix[1:]
            })
    return {"outputs": sorted(outputs, key=lambda x: x['created'], reverse=True)}

# MCP metadata endpoint
@api_v1.get("/mcp/metadata")
async def get_metadata(current_user: str = Depends(verify_token)):
    """Return MCP server metadata"""
    return {
        "name": "synthetic-data-mcp",
        "version": "1.0.0",
        "description": "PH Retail synthetic data generator with TBWA client footprint",
        "tools": [
            {
                "name": "generate_data",
                "description": "Generate synthetic retail data",
                "parameters": {
                    "dataset_type": "string (transactions, inventory, customer_profiles)",
                    "num_records": "integer",
                    "start_date": "string (YYYY-MM-DD)",
                    "end_date": "string (YYYY-MM-DD)",
                    "client_weight": "float (0-1, default 0.55)",
                    "tobacco_share": "float (0-1, default 0.18)",
                    "output_format": "string (csv, json, parquet)"
                }
            },
            {
                "name": "validate_quality",
                "description": "Validate synthetic data quality",
                "parameters": {
                    "dataset_path": "string",
                    "validation_rules": "array[string] (completeness, distribution, outliers)"
                }
            },
            {
                "name": "simulate_scenario",
                "description": "Generate data for specific market scenarios",
                "parameters": {
                    "scenario": "string (normal, peak_season, competitor_promo, supply_shortage)",
                    "duration_days": "integer",
                    "affected_brands": "array[string]",
                    "impact_factor": "float (default 1.2)"
                }
            }
        ]
    }


# Include API v1 router
app.include_router(api_v1)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)