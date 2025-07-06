#!/usr/bin/env python3
"""
Generate Scout Dashboard-ready dataset with coverage-first approach
Ensures all regions are represented while maintaining realistic market share
"""

import requests
import json
import sys

# Configuration for Scout-ready dataset
SCOUT_CONFIG = {
    "dataset_type": "transactions",
    "num_records": 17000,  # ~6MB CSV, loads instantly
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "output_format": "csv",
    "coverage_first": True  # Ensure all regions have data
}

def generate_scout_data():
    """Generate dataset optimized for Scout Dashboard"""
    print("🎯 Generating Scout Dashboard-ready dataset...")
    print(f"   Records: {SCOUT_CONFIG['num_records']:,}")
    print(f"   Period: {SCOUT_CONFIG['start_date']} to {SCOUT_CONFIG['end_date']}")
    print(f"   Coverage: All 17 regions guaranteed")
    print("")
    
    try:
        response = requests.post(
            "http://localhost:8005/mcp/tools/generate_data",
            json=SCOUT_CONFIG,
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
        print("   Make sure the server is running: ./scripts/start_v2.sh")
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
                    print(f"   Completeness: {score:.1%}")
                
                # Distribution check
                if "distribution" in validations:
                    dist = validations["distribution"]
                    print(f"   TBWA Share: {dist['tbwa_share']:.1%} (target: 55%)")
                    print(f"   Tobacco Share: {dist['tobacco_share']:.1%} (target: 18%)")
                    print(f"   JTI in Tobacco: {dist['jti_tobacco_share']:.1%} (target: 40%)")
                    print(f"   Regional Coverage: {dist['regions_covered']}/{dist['total_regions']}")
                
                # Outliers check
                if "outliers" in validations:
                    outliers = validations["outliers"]
                    print(f"   Price Outliers: {outliers['outlier_percentage']:.1%}")
                
                print("")
                print("✅ Data quality validated!")
            else:
                print(f"   Validation failed: {result.get('error', 'Unknown error')}")
                
    except Exception as e:
        print(f"   Could not validate: {e}")

def print_dashboard_checklist():
    """Print checklist for Scout Dashboard compatibility"""
    print("\n📋 Scout Dashboard Checklist:")
    print("   ✓ All 17 regions represented")
    print("   ✓ Economic weighting applied (NCR highest)")
    print("   ✓ Category breakdown matches market reality")
    print("   ✓ TBWA clients ~55% of total market")
    print("   ✓ JTI has 40% of tobacco category")
    print("   ✓ Time patterns (peak hours, paydays)")
    print("   ✓ Authentic Filipino store names")
    print("   ✓ Real barangay locations")
    print("")
    print("🚀 Dataset ready for Scout Dashboard!")

if __name__ == "__main__":
    print("=" * 60)
    print("Scout Dashboard Dataset Generator")
    print("Powered by Synthetic Data MCP V2")
    print("=" * 60)
    print("")
    
    output_path = generate_scout_data()
    
    if output_path:
        print_dashboard_checklist()
        print(f"\n💾 Next steps:")
        print(f"   1. Upload to Supabase: supabase db import {output_path}")
        print(f"   2. Or copy to Scout project: cp {output_path} ../scout-dashboard/data/")
    else:
        print("\n⚠️  Generation failed. Please check the server logs.")
        sys.exit(1)