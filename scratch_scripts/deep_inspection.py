import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient
import bson

load_dotenv(dotenv_path="../.env")
DB_URI = os.getenv("PRITHU_DB_URI")
DB_NAME = os.getenv("PRITHU_DB_NAME")

def inspect_data():
    client = MongoClient(DB_URI)
    db = client[DB_NAME]
    
    print("\n--- 1. SAMPLE FEED WITH WATCH TIME ---")
    feed = db["Feeds"].find_one({"playbackStats.totalWatchTime": {"$gt": 0}})
    if feed:
        print(f"Feed ID: {feed['_id']}")
        print(f"Watch Time: {feed.get('playbackStats', {}).get('totalWatchTime')} seconds")
        print(f"Completion Rate: {feed.get('playbackStats', {}).get('completionRate')}%")
        
    print("\n--- 2. SAMPLE USER FEED ANALYTICS ---")
    analytics = db["UserFeedAnalytics"].find_one()
    if analytics:
        # handle ObjectId
        for k, v in analytics.items():
            if isinstance(v, bson.ObjectId):
                analytics[k] = str(v)
        print(json.dumps(analytics, indent=2, default=str))

    print("\n--- 3. SAMPLE USER ACTIVITIES ---")
    activity = db["UserActivities"].find_one()
    if activity:
        for k, v in activity.items():
            if isinstance(v, bson.ObjectId):
                activity[k] = str(v)
        print(json.dumps(activity, indent=2, default=str))

if __name__ == "__main__":
    inspect_data()
