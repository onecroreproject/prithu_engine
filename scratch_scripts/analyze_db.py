import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv(dotenv_path="../.env")

DB_URI = os.getenv("PRITHU_DB_URI")
DB_NAME = os.getenv("PRITHU_DB_NAME")

def analyze_database():
    if not DB_URI or not DB_NAME:
        print("Error: PRITHU_DB_URI or PRITHU_DB_NAME is not set.")
        return

    print(f"Connecting to MongoDB Atlas...")
    client = MongoClient(DB_URI)
    db = client[DB_NAME]
    
    print(f"Connected to database: {DB_NAME}")
    
    collections_to_check = [
        "Categories", "Feeds", "Users", "UserFeedAnalytics", 
        "UserSeenHistory", "DailyFeeds", "TimeSlots", "GodConfig"
    ]
    
    print("\n--- Collection Volumes ---")
    for col_name in collections_to_check:
        try:
            count = db[col_name].count_documents({})
            print(f"{col_name}: {count} documents")
        except Exception as e:
            print(f"{col_name}: Error - {str(e)}")
            
    print("\n--- Sample Document: Feeds ---")
    try:
        sample_feed = db["Feeds"].find_one()
        if sample_feed:
            # Remove _id as it might not be JSON serializable
            sample_feed['_id'] = str(sample_feed.get('_id'))
            print(json.dumps(sample_feed, indent=2, default=str))
        else:
            print("No documents found in Feeds collection.")
    except Exception as e:
        print(f"Error fetching sample feed: {str(e)}")
        
    print("\n--- Sample Document: Categories ---")
    try:
        sample_category = db["Categories"].find_one()
        if sample_category:
            sample_category['_id'] = str(sample_category.get('_id'))
            print(json.dumps(sample_category, indent=2, default=str))
        else:
            print("No documents found in Categories collection.")
    except Exception as e:
        print(f"Error fetching sample category: {str(e)}")

    print("\n--- Indexes: Feeds ---")
    try:
        indexes = db["Feeds"].index_information()
        for name, info in indexes.items():
            print(f"Index name: {name}, Info: {info}")
    except Exception as e:
        print(f"Error fetching indexes for Feeds: {str(e)}")

if __name__ == "__main__":
    analyze_database()
