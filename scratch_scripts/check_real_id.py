import sys
sys.path.append('.')
from app.database.db_connection import get_db_manager
from bson import ObjectId

user_id = "6923e91497388df4028311b1"
db = get_db_manager()

print(f"=== CHECKING ANALYTICS FOR ID: {user_id} ===")
try:
    count = db._db.UserFeedAnalytics.count_documents({"userId": user_id})
    print(f"Total analytics records for this ID: {count}")
    
    if count > 0:
        recent = list(db._db.UserFeedAnalytics.find({"userId": user_id}).sort("createdAt", -1).limit(5))
        for r in recent:
            print(f" - Feed: {r.get('feedId')} | Watched: {r.get('percentageWatched')}% | Liked: {r.get('liked')}")
            
    prefs = db._db.UserCategorys.find_one({"userId": user_id})
    if prefs:
        print(f"\nUser Category Preferences found! Not Interested count: {len(prefs.get('nonInterestedCategories', []))}")
    else:
        print("\nNo User Category Preferences found.")
        
except Exception as e:
    print(f"Error: {e}")
