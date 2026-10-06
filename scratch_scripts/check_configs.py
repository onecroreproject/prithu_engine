import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(dotenv_path="../.env")
DB_URI = os.getenv("PRITHU_DB_URI")
DB_NAME = os.getenv("PRITHU_DB_NAME")

def check_configs():
    client = MongoClient(DB_URI)
    db = client[DB_NAME]
    
    print("\n--- CHECKING TimeSlots COLLECTION ---")
    time_slots = list(db["TimeSlots"].find({}, {"_id": 0}))
    if not time_slots:
        print("TimeSlots collection is EMPTY (0 records).")
    else:
        print(f"Found {len(time_slots)} records in TimeSlots:")
        print(json.dumps(time_slots, indent=2))

    print("\n--- CHECKING GodConfig COLLECTION ---")
    god_configs = list(db["GodConfig"].find({}, {"_id": 0}))
    if not god_configs:
        print("GodConfig collection is EMPTY (0 records).")
    else:
        print(f"Found {len(god_configs)} records in GodConfig:")
        print(json.dumps(god_configs, indent=2))

if __name__ == "__main__":
    check_configs()
