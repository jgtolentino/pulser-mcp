#!/usr/bin/env python3
"""
Seed Qdrant with sample creative assets data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import random
from datetime import datetime, timedelta
import httpx

# Sample creative data
BRANDS = ["Nike", "Coca-Cola", "Apple", "Samsung", "Toyota", "McDonald's", "P&G", "Unilever"]

CAMPAIGNS = {
    "Nike": ["Just Do It 2024", "Air Max Revolution", "Sustainability Heroes"],
    "Coca-Cola": ["Share a Coke", "Taste the Feeling", "Real Magic"],
    "Apple": ["Think Different Redux", "Shot on iPhone", "Privacy Matters"],
    "Samsung": ["Galaxy Unpacked", "Do What You Can't", "Next Normal"],
    "Toyota": ["Let's Go Places", "Start Your Impossible", "Hybrid Evolution"],
    "McDonald's": ["I'm Lovin' It", "Famous Orders", "McDelivery Joy"],
    "P&G": ["Force of Good", "Lead with Love", "Home Heroes"],
    "Unilever": ["Planet Positive", "Unstereotype", "Wellbeing Collective"]
}

ASSET_TYPES = ["storyboard", "thumbnail", "video_frame", "creative_brief"]

CREATIVE_CONCEPTS = [
    "Minimalist design with bold typography",
    "Emotional storytelling through user testimonials",
    "Vibrant colors with dynamic motion graphics",
    "Black and white photography with striking contrasts",
    "Illustrated characters in everyday situations",
    "Abstract visualization of product benefits",
    "Cinematic wide shots with epic music",
    "Close-up product shots with ASMR elements",
    "Split-screen comparisons showing transformation",
    "Time-lapse sequences showing progress"
]

AWARDS = ["Cannes Lions Gold", "D&AD Pencil", "One Show Merit", "Clio Bronze", "Webby Winner"]

async def seed_creative_assets():
    """Seed Qdrant with sample creative assets"""
    base_url = "http://localhost:8001"
    
    print("🎨 Seeding Creative RAG with sample assets...")
    
    async with httpx.AsyncClient() as client:
        assets_created = 0
        
        for brand in BRANDS:
            campaigns = CAMPAIGNS.get(brand, ["Generic Campaign"])
            
            for campaign in campaigns:
                # Generate 5-10 assets per campaign
                num_assets = random.randint(5, 10)
                
                for i in range(num_assets):
                    asset_type = random.choice(ASSET_TYPES)
                    asset_id = f"{brand.lower().replace(' ', '_')}_{campaign.lower().replace(' ', '_')}_{asset_type}_{i+1}"
                    
                    # Generate metadata
                    metadata = {
                        "creator": f"Creative Team {random.randint(1, 5)}",
                        "date_created": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
                        "tags": random.sample(["innovative", "emotional", "bold", "minimalist", "vibrant", "storytelling"], 3),
                        "performance_score": round(random.uniform(70, 95), 1)
                    }
                    
                    # Add awards randomly
                    if random.random() > 0.7:
                        metadata["awards"] = [random.choice(AWARDS)]
                    
                    # Create asset data
                    asset_data = {
                        "asset_id": asset_id,
                        "asset_type": asset_type,
                        "brand": brand,
                        "campaign": campaign,
                        "metadata": metadata,
                        "text_content": f"{random.choice(CREATIVE_CONCEPTS)} for {brand} {campaign} campaign"
                    }
                    
                    # Send to API
                    try:
                        response = await client.post(
                            f"{base_url}/mcp/tools/ingest_asset",
                            json=asset_data
                        )
                        if response.status_code == 200:
                            assets_created += 1
                            print(f"✓ Created: {asset_id}")
                        else:
                            print(f"✗ Failed: {asset_id} - {response.text}")
                    except Exception as e:
                        print(f"✗ Error: {asset_id} - {str(e)}")
        
        print(f"\n✅ Successfully created {assets_created} creative assets")
        
        # Test search
        print("\n🔍 Testing vector search...")
        test_queries = [
            "minimalist design campaigns",
            "emotional storytelling",
            "award winning Nike campaigns",
            "sustainable brand messaging"
        ]
        
        for query in test_queries:
            try:
                response = await client.post(
                    f"{base_url}/mcp/tools/search_vector",
                    json={
                        "query": query,
                        "query_type": "text",
                        "top_k": 3
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    print(f"\nQuery: '{query}'")
                    print(f"Found {result['results_count']} results")
                    for r in result['results'][:3]:
                        print(f"  - {r['brand']} / {r['campaign']} ({r['score']:.3f})")
            except Exception as e:
                print(f"Search error: {str(e)}")

def main():
    """Run the seeding process"""
    # Check if server is running
    import requests
    try:
        response = requests.get("http://localhost:8001/")
        if response.status_code != 200:
            print("❌ Creative RAG server is not running. Please start it first.")
            return
    except:
        print("❌ Cannot connect to Creative RAG server at http://localhost:8001")
        print("Please run: python src/rag_server.py")
        return
    
    # Run async seeding
    asyncio.run(seed_creative_assets())

if __name__ == "__main__":
    main()