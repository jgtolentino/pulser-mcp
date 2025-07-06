#!/usr/bin/env python3
"""
Seed the Scout Local database with sample transcription data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Sample data
REGIONS = ["NCR", "CALABARZON", "Central Luzon", "Central Visayas", "Davao Region"]
STORES = {
    "NCR": ["SM-NCR-001", "SM-NCR-002", "ROB-NCR-001", "AYA-NCR-001"],
    "CALABARZON": ["SM-CAL-001", "ROB-CAL-001", "WAL-CAL-001"],
    "Central Luzon": ["SM-CL-001", "ROB-CL-001"],
    "Central Visayas": ["SM-CV-001", "AYA-CV-001"],
    "Davao Region": ["SM-DAV-001", "NCCC-DAV-001"]
}

BRANDS = [
    "Nike", "Adidas", "Puma", "Under Armour", "New Balance",
    "Uniqlo", "H&M", "Zara", "Forever 21", "Cotton On",
    "Samsung", "Apple", "Xiaomi", "Oppo", "Vivo",
    "Nestle", "P&G", "Unilever", "Colgate", "Johnson & Johnson"
]

SAMPLE_TRANSCRIPTS = [
    "Customer asked about {brand} product availability. Showed them latest collection.",
    "Inquiry about {brand} pricing and ongoing promotions. Customer seemed interested.",
    "Demonstrated {brand} features. Customer comparing with competitors.",
    "Regular customer looking for {brand} new arrivals. Made a purchase.",
    "Group of customers browsing {brand} section. Provided product information.",
    "Customer complaint about {brand} quality. Escalated to manager.",
    "Successful upsell of {brand} accessories. Customer satisfied.",
    "Stock check for {brand} requested. Item out of stock, took pre-order.",
    "Price match request for {brand}. Approved by supervisor.",
    "Customer loyalty member interested in {brand} exclusive offers."
]

def seed_database():
    """Seed the database with sample data"""
    db_path = Path(__file__).parent.parent / "data" / "scout_local.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🌱 Seeding Scout Local database...")
    
    # Generate sample data for the past 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    entries_created = 0
    
    for day in range(30):
        current_date = start_date + timedelta(days=day)
        
        # Generate 50-100 transcriptions per day
        daily_transcriptions = random.randint(50, 100)
        
        for _ in range(daily_transcriptions):
            region = random.choice(REGIONS)
            store_id = random.choice(STORES[region])
            brand = random.choice(BRANDS)
            transcript_template = random.choice(SAMPLE_TRANSCRIPTS)
            transcript = transcript_template.format(brand=brand)
            
            # Random time during business hours (9 AM - 9 PM)
            hour = random.randint(9, 21)
            minute = random.randint(0, 59)
            timestamp = current_date.replace(hour=hour, minute=minute)
            
            # Generate metadata
            metadata = {
                "agent_id": f"field_{random.randint(1, 20):03d}",
                "device_id": f"tablet_{random.randint(1, 50):02d}",
                "duration_seconds": random.randint(30, 300),
                "customer_type": random.choice(["new", "returning", "loyalty"]),
                "interaction_type": random.choice(["inquiry", "purchase", "complaint", "browse"])
            }
            
            cursor.execute("""
                INSERT INTO bronze_transcriptions 
                (store_id, region, brand, transcript, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                store_id,
                region,
                brand,
                transcript,
                json.dumps(metadata),
                timestamp
            ))
            
            entries_created += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ Successfully created {entries_created} sample transcriptions")
    print(f"📊 Data spans from {start_date.date()} to {end_date.date()}")
    print("\nSample brands included:")
    for i in range(0, len(BRANDS), 5):
        print(f"  {', '.join(BRANDS[i:i+5])}")
    print(f"\nRegions covered: {', '.join(REGIONS)}")

if __name__ == "__main__":
    seed_database()