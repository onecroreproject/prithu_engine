import sys
sys.path.append('.')
from app.database.db_connection import get_db_manager
from bson import ObjectId
from collections import defaultdict

db = get_db_manager()

print("=== DB COLLECTIONS ===")
print(db._db.list_collection_names())

print("\n=== FINDING TOP USER ===")
pipeline = [
    {"$group": {"_id": "$userId", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 1}
]
top_user_cursor = list(db._db.UserFeedAnalytics.aggregate(pipeline))

if not top_user_cursor:
    print("No users found.")
    sys.exit(0)
    
target_user = top_user_cursor[0]["_id"]
print(f"Target User: {target_user} (Total interactions: {top_user_cursor[0]['count']})")

print("\n=== EXTRACTING USER DATA ===")
# 1 & 2 & 3 & 5. Categories, Images vs Videos, Watch Time
analytics = db.find_many('UserFeedAnalytics', {'userId': target_user}, limit=1000)

categories_watched = defaultdict(int)
videos_seen = []
images_seen = []
total_watch_seconds = 0.0

for a in analytics:
    feed_id = a.get('feedId')
    if feed_id:
        try:
            feed = db.find_one('Feeds', {'_id': ObjectId(feed_id) if isinstance(feed_id, str) and len(feed_id)==24 else feed_id})
        except:
            feed = None
            
        if feed:
            cats = feed.get('category', [])
            cat_str = str(cats[0]) if cats else "Unknown"
            categories_watched[cat_str] += 1
            
            post_type = feed.get('postType', 'image')
            if 'video' in post_type.lower():
                videos_seen.append(str(feed_id))
            else:
                images_seen.append(str(feed_id))
            
            # Watch time (assume percentageWatched * feed duration, or just record percentage)
            watch_time_sec = a.get('watchTime', 0.0) # Check if watchTime exists
            total_watch_seconds += float(watch_time_sec)

# 4. Not interested categories
user_prefs = db.find_one('UserCategorys', {'userId': target_user})
not_interested = []
if user_prefs:
    not_interested = user_prefs.get('nonInterestedCategories', [])

# Resolve Category Names
cat_names = {}
for cid in categories_watched.keys():
    if cid != "Unknown":
        try:
            c = db.find_one('Categories', {'_id': ObjectId(cid)})
            cat_names[cid] = c.get('name', cid) if c else cid
        except:
            cat_names[cid] = cid

print("\n--- REPORT FOR USER ---")
print("1. Categories Watched (Count):")
for cid, count in sorted(categories_watched.items(), key=lambda x: x[1], reverse=True):
    print(f"   - {cat_names.get(cid, cid)}: {count} times")

print(f"\n2. Images Seen: {len(images_seen)}")
print(f"3. Videos Seen: {len(videos_seen)}")
print(f"4. Not Interested Categories: {len(not_interested)} {not_interested}")
print(f"5. Total Watch Time Recorded: {total_watch_seconds / 60.0:.2f} minutes")

