import pymongo, os
from dotenv import load_dotenv
from bson.objectid import ObjectId

load_dotenv('.env')
db = pymongo.MongoClient(os.getenv('PRITHU_DB_URI'))[os.getenv('PRITHU_DB_NAME')]

uid = ObjectId('6923e91497388df4028311b1')

print("=== PROFILE DETAILS ===")
user = db.users.find_one({'_id': uid}) or db.Users.find_one({'_id': uid}) or db.User.find_one({'_id': uid})
if user:
    for k, v in user.items():
        if k not in ['password', 'hash', 'salt', 'fcmToken', 'tokens', 'fcmTokens']:
            if isinstance(v, dict):
                print(f"{k}:")
                for sub_k, sub_v in v.items():
                    print(f"  - {sub_k}: {sub_v}")
            else:
                print(f"{k}: {v}")

print("\n=== USER ACTIVITIES (Last 100) ===")
acts = list(db.UserActivities.find({'userId': uid}).sort('createdAt', -1).limit(100))
print(f"Found {len(acts)} recent activities.")

actions_count = {}
cats = {}
for a in acts:
    action = a.get('actionType')
    actions_count[action] = actions_count.get(action, 0) + 1
    
    if a.get('targetModel') == 'Feed' or 'FEED' in str(action) or 'POST' in str(action):
        feed = db.Feeds.find_one({'_id': a.get('targetId')}) or db.feeds.find_one({'_id': a.get('targetId')})
        if feed and feed.get('category'):
            c = feed.get('category')
            c = c[0] if isinstance(c, list) else c
            cat_doc = db.categories.find_one({'_id': c}) or db.Categories.find_one({'_id': c})
            c_name = cat_doc.get('name', str(c)) if cat_doc else str(c)
            cats[c_name] = cats.get(c_name, 0) + 1

print("Actions Breakdown:", actions_count)
print("Top Categories Interacted With:", cats)

print("\n=== LIFETIME SEEN HISTORY ===")
seen = db.UserSeenHistory.find_one({'userId': uid})
if seen:
    feeds = seen.get('seenFeedIds', [])
    print(f"You have seen {len(feeds)} different feeds in your lifetime.")
else:
    print("No seen history found.")

print("\n=== FEED ANALYTICS / ML DATA ===")
analytics = list(db.UserFeedAnalytics.find({'userId': uid}).sort('createdAt', -1).limit(10))
print(f"Found {len(analytics)} records in ML analytics (showing latest {len(analytics)}):")
for an in analytics:
    print(f"Feed: {an.get('feedId')}, Watched: {an.get('percentageWatched', 0)}%, Liked: {an.get('liked', False)}, Replays: {an.get('replayCount', 0)}")
