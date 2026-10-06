import sys
sys.path.append('.')
from app.database.db_connection import get_db_manager
from bson import ObjectId
from datetime import datetime, timedelta

user_id = "google_TDubsbd6D8MGenHmT41H8AzVqNM2"
db = get_db_manager()

print("=== CHECKING SUBCATEGORIES ===")
try:
    subcategories = db._db.Feeds.distinct("subCategory")
    print(f"Total distinct subcategories: {len(subcategories)}")
    
    # Safely print matching subcategories
    matches = [s for s in subcategories if s and any(k in str(s).lower() for k in ['murugan', 'murugar', 'lakshmi', 'abdul', 'kalam'])]
    print("Matching Subcategories:")
    for m in matches:
        # Encode to ascii to drop emojis safely on windows console
        safe_str = str(m).encode('ascii', 'ignore').decode('ascii')
        print(f" - {safe_str}")
        
except Exception as e:
    print(f"Error checking subcats: {e}")
    
print(f"\n=== CHECKING FEED HISTORY (LAST 24 HOURS) FOR: {user_id} ===")
try:
    one_day_ago = datetime.utcnow() - timedelta(hours=24)
    recent_analytics = list(db._db.UserFeedAnalytics.find({
        "userId": user_id,
        "createdAt": {"$gte": one_day_ago}
    }))
    recent_seen = list(db._db.UserSeenHistory.find({
        "userId": user_id,
        "viewedAt": {"$gte": one_day_ago}
    }))
    
    seen_feed_ids = set()
    for doc in recent_analytics:
        if "feedId" in doc: seen_feed_ids.add(str(doc["feedId"]))
    for doc in recent_seen:
        if "feedId" in doc: seen_feed_ids.add(str(doc["feedId"]))
        if "seenFeedIds" in doc: 
            for fid in doc["seenFeedIds"]: seen_feed_ids.add(str(fid))
            
    print(f"Found {len(seen_feed_ids)} distinct feeds seen in the last 24 hours.")
    
    if seen_feed_ids:
        feed_object_ids = []
        for fid in seen_feed_ids:
            try: feed_object_ids.append(ObjectId(fid) if len(fid)==24 else fid)
            except: feed_object_ids.append(fid)
                
        recent_feeds = list(db._db.Feeds.find({"_id": {"$in": feed_object_ids}}))
        
        cat_counts = {}
        for feed in recent_feeds:
            cats = feed.get("category", [])
            cat_id = str(cats[0]) if cats else "Unknown"
            
            c_doc = db.find_one("Categories", {"_id": ObjectId(cat_id) if len(cat_id)==24 else cat_id})
            cat_name = c_doc.get("name", cat_id) if c_doc else cat_id
            cat_name = str(cat_name).encode('ascii', 'ignore').decode('ascii')
            cat_counts[cat_name] = cat_counts.get(cat_name, 0) + 1
            
        print("\nCategories Seen:")
        for c, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
            print(f" - {c}: {count}")
except Exception as e:
    print(f"Error checking recent history: {e}")
