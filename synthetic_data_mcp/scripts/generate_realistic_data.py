#!/usr/bin/env python3
"""
Generate realistic PH retail dataset with proper market share distribution
Uses V3 server with 177 brands and realistic category weights
"""

import requests
import json
import sys
import os

# Configuration for realistic dataset
REALISTIC_CONFIG = {
    "dataset_type": "transactions",
    "num_records": 17000,  # Coverage-first for all regions
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "output_format": "csv",
    "coverage_first": True
}

def generate_realistic_data():
    """Generate dataset with realistic market share (~22% TBWA)"""
    print("🏪 Generating Realistic PH Sari-Sari Store Dataset...")
    print(f"   Records: {REALISTIC_CONFIG['num_records']:,}")
    print(f"   Expected TBWA Share: ~22% (realistic market penetration)")
    print(f"   Brands: 177 total (39 TBWA clients + 138 competitors)")
    print(f"   Categories: 17 major sari-sari categories")
    print("")
    
    try:
        response = requests.post(
            "http://localhost:8005/mcp/tools/generate_data",
            json=REALISTIC_CONFIG,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success"):
                print("✅ Generation successful!")
                print(f"📄 Output: {result['output_path']}")
                print("")
                print("📊 Market Share Summary:")
                summary = result.get('summary', {})
                print(f"   TBWA Client Share: {summary.get('tbwa_client_share', 0):.1%}")
                print(f"   Tobacco Share: {summary.get('tobacco_share', 0):.1%}")
                print(f"   JTI within Tobacco: {summary.get('jti_tobacco_share', 0):.1%}")
                print(f"   Regions Covered: {summary.get('regions_covered', 0)}/17")
                print("")
                
                # Show category breakdown
                cat_dist = summary.get('category_distribution', {})
                if cat_dist:
                    print("📈 Category Distribution:")
                    for cat, pct in sorted(cat_dist.items(), key=lambda x: x[1], reverse=True):
                        print(f"   {cat}: {pct:.1%}")
                    print("")
                
                # Show TBWA presence by category
                tbwa_by_cat = summary.get('tbwa_by_category', {})
                if tbwa_by_cat:
                    print("🎯 TBWA Share by Category:")
                    for cat, share in sorted(tbwa_by_cat.items(), key=lambda x: x[1], reverse=True):
                        if share > 0:
                            print(f"   {cat}: {share:.1%}")
                    print("")
                
                # Validate the generated data
                validate_data(result['output_path'])
                
                return result['output_path']
            else:
                print(f"❌ Generation failed: {result.get('error', 'Unknown error')}")
                return None
        else:
            print(f"❌ Server error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server")
        print("   Make sure the V3 server is running:")
        print("   python src/synthetic_server_v3.py")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def validate_data(file_path):
    """Validate the generated dataset"""
    print("🔍 Validating data quality...")
    
    validation_request = {
        "dataset_path": file_path,
        "validation_rules": ["completeness", "distribution", "outliers"]
    }
    
    try:
        response = requests.post(
            "http://localhost:8005/mcp/tools/validate_quality",
            json=validation_request
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success"):
                validations = result.get("validation_results", {})
                
                # Completeness check
                if "completeness" in validations:
                    score = validations["completeness"]["completeness_score"]
                    print(f"   ✓ Completeness: {score:.1%}")
                
                # Distribution check
                if "distribution" in validations:
                    dist = validations["distribution"]
                    expected = dist.get("expected_tbwa_share", 0.22)
                    actual = dist["tbwa_share"]
                    variance = abs(actual - expected) / expected
                    
                    print(f"   ✓ TBWA Share: {actual:.1%} (expected: {expected:.1%})")
                    if variance < 0.1:
                        print("     ✅ Within acceptable range")
                    else:
                        print("     ⚠️ Outside expected range")
                    
                    print(f"   ✓ Tobacco Share: {dist['tobacco_share']:.1%}")
                    print(f"   ✓ JTI in Tobacco: {dist['jti_tobacco_share']:.1%}")
                    print(f"   ✓ Regional Coverage: {dist['regions_covered']}/{dist['total_regions']}")
                
                # Outliers check
                if "outliers" in validations:
                    outliers = validations["outliers"]
                    print(f"   ✓ Price Outliers: {outliers['outlier_percentage']:.1%}")
                    print(f"   ✓ Price Range: ₱{outliers['price_range']['min']:.0f} - ₱{outliers['price_range']['max']:.0f}")
                
                print("")
                print("✅ Data quality validated!")
            else:
                print(f"   ❌ Validation failed: {result.get('error', 'Unknown error')}")
                
    except Exception as e:
        print(f"   ⚠️ Could not validate: {e}")

def print_market_reality_summary():
    """Print summary of realistic market modeling"""
    print("\n📋 Realistic Market Modeling Summary:")
    print("")
    print("🏪 Sari-Sari Store Category Mix (% of transactions):")
    print("   ├─ Snacks: 14% (chips, crackers, biscuits)")
    print("   ├─ Tobacco: 14% (cigarettes)")
    print("   ├─ Beverages: 9% (juice, water, energy drinks)")
    print("   ├─ Home Care: 8% (detergent, cleaning)")
    print("   ├─ CSD: 7% (Coke, Pepsi, Sprite)")
    print("   ├─ Dairy: 7% (milk products)")
    print("   ├─ Rice: 7% (staple grain)")
    print("   ├─ Noodles: 6% (instant noodles)")
    print("   ├─ Personal Care: 6% (shampoo, soap)")
    print("   ├─ Condiments: 4% (sauces, seasonings)")
    print("   └─ Others: 18% (various categories)")
    print("")
    print("🎯 TBWA Client Penetration by Category:")
    print("   ├─ Canned Goods: 70% (Del Monte fruit cocktail)")
    print("   ├─ Dairy: 50% (Alaska vs Bear Brand, Nestlé)")
    print("   ├─ Condiments: 40% (Del Monte sauces)")
    print("   ├─ Tobacco: 40% (JTI vs PMFTC, others)")
    print("   ├─ Snacks: 35% (Oishi vs URC, Monde Nissin)")
    print("   ├─ Beverages: 20% (Del Monte + Oishi vs majors)")
    print("   ├─ Home Care: 12% (Peerless vs P&G, Unilever)")
    print("   ├─ Personal Care: 10% (Peerless vs majors)")
    print("   └─ Others: 0-10% (limited presence)")
    print("")
    print("📊 Total Market Share:")
    print("   ├─ TBWA Clients: ~22% (realistic penetration)")
    print("   └─ Competitors: ~78% (multinationals + locals)")
    print("")
    print("🚀 This dataset reflects actual PH retail landscape!")

if __name__ == "__main__":
    print("=" * 70)
    print("Realistic PH Retail Dataset Generator")
    print("Powered by Synthetic Data MCP V3")
    print("177 Brands | Authentic Market Share | Coverage-First")
    print("=" * 70)
    print("")
    
    output_path = generate_realistic_data()
    
    if output_path:
        print_market_reality_summary()
        print(f"\n💾 Next steps:")
        print(f"   1. Upload to Supabase: supabase db import {output_path}")
        print(f"   2. Copy to Scout: cp {output_path} ../scout-dashboard/data/")
        print(f"   3. Verify in Scout Dashboard filters show all categories")
        print("")
        print("🎯 Perfect for realistic Scout Dashboard testing!")
    else:
        print("\n⚠️  Generation failed. Please check the server logs.")
        sys.exit(1)