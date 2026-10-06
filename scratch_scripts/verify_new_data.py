import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(dotenv_path="../.env")
DB_URI = os.getenv("PRITHU_DB_URI")
DB_NAME = os.getenv("PRITHU_DB_NAME")

def verify_new_data():
    client = MongoClient(DB_URI)
    db = client[DB_NAME]
    
    print("\n--- 1. VERIFYING percentageWatched (VIDEOS) ---")
    video_analytics = list(db["UserFeedAnalytics"].find(
        {"percentageWatched": {"$gt": 0}}
    ).sort("createdAt", -1).limit(2))
    
    if video_analytics:
        print(f"SUCCESS: Found records with percentageWatched > 0!")
        for rec in video_analytics:
            print(f" - FeedID: {rec.get('feedId')}, percentageWatched: {rec.get('percentageWatched')}%, watchTime: {rec.get('watchTime')}s")
    else:
        print("Waiting for new data... No records found with percentageWatched > 0 yet.")

    print("\n--- 2. VERIFYING scrollStopDuration (IMAGES) ---")
    image_analytics = list(db["UserFeedAnalytics"].find(
        {"scrollStopDuration": {"$gt": 0}}
    ).sort("createdAt", -1).limit(2))
    
    if image_analytics:
        print(f"SUCCESS: Found records with scrollStopDuration > 0!")
        for rec in image_analytics:
            print(f" - FeedID: {rec.get('feedId')}, scrollStopDuration: {rec.get('scrollStopDuration')}ms")
    else:
        print("Waiting for new data... No records found with scrollStopDuration > 0 yet.")

    print("\n--- 3. VERIFYING UserSeenHistory ---")
    seen_history = db["UserSeenHistory"].find_one()
    if seen_history:
        print(f"SUCCESS: Found UserSeenHistory record!")
        seen_history['_id'] = str(seen_history['_id'])
        if 'userId' in seen_history: seen_history['userId'] = str(seen_history['userId'])
        # just print keys to verify structure
        print(f"Keys in UserSeenHistory: {list(seen_history.keys())}")
        if 'viewedFeeds' in seen_history or 'feedIds' in seen_history:
            feeds_list = seen_history.get('viewedFeeds') or seen_history.get('feedIds') or []
            print(f"Number of feeds recorded for this user: {len(feeds_list)}")
    else:
        print("❌ Waiting for new data... UserSeenHistory is empty.")

if __name__ == "__main__":
    verify_new_data()
