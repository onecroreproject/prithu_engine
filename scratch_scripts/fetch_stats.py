import pymongo, os, datetime
from dotenv import load_dotenv
load_dotenv('.env')
db = pymongo.MongoClient(os.getenv('PRITHU_DB_URI'))[os.getenv('PRITHU_DB_NAME')]
uid = 'google_TDubsbd6D8MGenHmT41H8AzVqNM2'
today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

docs = list(db.UserFeedAnalytics.find({'userId': uid, 'createdAt': {'$gte': today}}))
print(f'Analytics today: {len(docs)}')

seen = db.UserSeenHistory.find_one({'userId': uid})
print(f'Lifetime seen feeds: {len(seen.get("seenFeedIds", [])) if seen else 0}')

cats = {}
for d in docs:
    feed = db.Feeds.find_one({'_id': d.get('feedId')}) or db.feeds.find_one({'_id': d.get('feedId')})
    if feed and feed.get('category'):
        c = feed.get('category')
        c = c[0] if isinstance(c, list) else c
        
        # Get category name
        cat_doc = db.categories.find_one({'_id': c}) or db.Categories.find_one({'_id': c})
        c_name = cat_doc.get('name', str(c)) if cat_doc else str(c)
        cats[c_name] = cats.get(c_name, 0) + 1
        
print('Categories seen today:', cats)
