import pymongo, os
from dotenv import load_dotenv
load_dotenv('.env')
db = pymongo.MongoClient(os.getenv('PRITHU_DB_URI'))[os.getenv('PRITHU_DB_NAME')]

uid = 'google_TDubsbd6D8MGenHmT41H8AzVqNM2'

print("--- UserActivities ---")
acts = list(db.UserActivities.find({'userId': uid}).sort('createdAt', -1).limit(100))
print(f"Found {len(acts)} activities.")
if acts:
    for a in acts[:5]:
        print(f"Action: {a.get('actionType')}, Date: {a.get('createdAt')}")

print("\n--- UserFeedAnalytics ---")
analytics = list(db.UserFeedAnalytics.find({'userId': uid}).sort('createdAt', -1).limit(100))
print(f"Found {len(analytics)} analytics.")

print("\n--- UserSeenHistory ---")
seen = db.UserSeenHistory.find_one({'userId': uid})
if seen:
    feeds = seen.get('seenFeedIds', [])
    print(f"Found {len(feeds)} seen feeds.")
else:
    print("No seen history found.")

print("\n--- UserFeedActions ---")
feed_acts = list(db.UserFeedActions.find({'userId': uid}).sort('createdAt', -1).limit(100))
print(f"Found {len(feed_acts)} feed actions.")
