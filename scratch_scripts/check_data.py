import sys
sys.path.append('.')
from app.database.db_connection import get_db_manager
from bson import ObjectId

db = get_db_manager()
analytics = db.find_many('UserFeedAnalytics', {}, limit=5, sort=[('createdAt', -1)])
print('--- Recent User Activity ---')
for a in analytics:
    feed_id = a.get('feedId')
    feed = None
    if feed_id:
        try:
            feed = db.find_one('Feeds', {'_id': ObjectId(feed_id) if isinstance(feed_id, str) and len(feed_id)==24 else feed_id})
        except:
            pass
            
    cat = feed.get('category') if feed else 'Unknown'
    # Use standard ascii dashes to avoid cp1252 error on windows
    print(f"User: {a.get('userId')}")
    print(f"  - Feed ID: {feed_id} | Category: {cat}")
    print(f"  - Watched: {a.get('percentageWatched', 0)}% | Liked: {a.get('liked')} | Skipped: {a.get('skipped')}")
    print("-")
