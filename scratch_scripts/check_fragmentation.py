import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(dotenv_path="../.env")
DB_URI = os.getenv("PRITHU_DB_URI")
DB_NAME = os.getenv("PRITHU_DB_NAME")

def check_fragmentation():
    client = MongoClient(DB_URI)
    db = client[DB_NAME]
    
    print("--- 1. CHECKING COLLECTION FRAGMENTATION ---")
    all_collections = db.list_collection_names()
    
    target_names = ["user", "category", "analytics", "stat", "post", "feed"]
    
    for target in target_names:
        matches = [c for c in all_collections if target in c.lower()]
        if matches:
            print(f"\nVariations for '{target}':")
            for m in sorted(matches):
                count = db[m].count_documents({})
                print(f" - {m}: {count} records")

    print("\n--- 2. CHECKING BLIND WATCH-TIME (FEEDS) ---")
    # Let's check how many feeds have watch time > 0 vs 0
    total_feeds = db["Feeds"].count_documents({})
    
    feeds_with_watch_time = db["Feeds"].count_documents({"playbackStats.totalWatchTime": {"$gt": 0}})
    feeds_with_0_watch_time = db["Feeds"].count_documents({"$or": [{"playbackStats.totalWatchTime": 0}, {"playbackStats.totalWatchTime": {"$exists": False}}]})
    
    feeds_with_completion = db["Feeds"].count_documents({"playbackStats.completionRate": {"$gt": 0}})
    feeds_with_0_completion = db["Feeds"].count_documents({"$or": [{"playbackStats.completionRate": 0}, {"playbackStats.completionRate": {"$exists": False}}]})
    
    print(f"Total Feeds: {total_feeds}")
    print(f"Feeds with Total Watch Time > 0: {feeds_with_watch_time}")
    print(f"Feeds with Total Watch Time = 0 (or missing): {feeds_with_0_watch_time}")
    print(f"Feeds with Completion Rate > 0: {feeds_with_completion}")
    print(f"Feeds with Completion Rate = 0 (or missing): {feeds_with_0_completion}")

    print("\n--- 3. CHECKING USER FEED ANALYTICS ---")
    # Check if UserFeedAnalytics has any data at all, or if there's a lowercase version
    analytics_colls = [c for c in all_collections if "userfeedanalytics" in c.lower()]
    for ac in analytics_colls:
        count = db[ac].count_documents({})
        print(f"{ac}: {count} records")

if __name__ == "__main__":
    check_fragmentation()
