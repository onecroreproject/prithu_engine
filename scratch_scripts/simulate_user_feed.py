import sys
sys.path.append('.')
from app.engine.optimizer import get_optimizer
from app.database.db_connection import get_db_manager
from collections import defaultdict
import datetime
from bson import ObjectId

user_id = "google_TDubsbd6D8MGenHmT41H8AzVqNM2"

optimizer = get_optimizer()
db = get_db_manager()

print(f"=== GENERATING DAILY FEED PLAN FOR USER: {user_id} ===")

try:
    # Generate 30 recommendations (Standard Daily Quota)
    recommendations = optimizer.get_recommendations(
        user_id=user_id,
        limit=30,
        diversity_boost=True,
        section="general"
    )
    
    if not recommendations:
        print("No recommendations returned. Either no feeds available or user blocked everything.")
        sys.exit(0)
        
    print(f"\nSuccessfully allocated {len(recommendations)} items for your daily feed.")
    
    categories = defaultdict(int)
    images_count = 0
    videos_count = 0
    
    for rec in recommendations:
        categories[rec.category] += 1
        
        # Check if feed is image or video
        feed = None
        try:
            feed = db.find_one("Feeds", {"_id": ObjectId(rec.feed_id) if len(rec.feed_id)==24 else rec.feed_id})
        except:
            pass
            
        if feed:
            ptype = feed.get("postType", "image").lower()
            if "video" in ptype:
                videos_count += 1
            else:
                images_count += 1
                
    print(f"\n--- YOUR PERSONALIZED MEDIA SPLIT ---")
    print(f"Videos Allocated: {videos_count}")
    print(f"Images Allocated: {images_count}")
    
    print("\n--- CATEGORY ALLOCATION BREAKDOWN ---")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f" - {cat}: {count} items")
        
except Exception as e:
    print(f"Error generating feed: {e}")
