import pymongo, os, datetime
from dotenv import load_dotenv
load_dotenv('.env')
db = pymongo.MongoClient(os.getenv('PRITHU_DB_URI'))[os.getenv('PRITHU_DB_NAME')]
today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# Check UserActivities collection
activities = list(db.UserActivities.find({'createdAt': {'$gte': today}}))
print(f"Total activities today: {len(activities)}")

if len(activities) == 0:
    # Maybe check without date filter just to see if we have ANY data
    all_activities = list(db.UserActivities.find().sort('createdAt', -1).limit(50))
    print(f"Total activities (all time): {len(all_activities)}")
    activities = all_activities

cats = {}
seen_feeds = 0
for a in activities:
    if a.get('actionType') in ['VIEW_FEED', 'WATCH_FEED', 'LIKE_POST'] and a.get('targetModel') == 'Feed':
        seen_feeds += 1
        feed = db.Feeds.find_one({'_id': a.get('targetId')}) or db.feeds.find_one({'_id': a.get('targetId')})
        if feed and feed.get('category'):
            c = feed.get('category')
            c = c[0] if isinstance(c, list) else c
            cat_doc = db.categories.find_one({'_id': c}) or db.Categories.find_one({'_id': c})
            c_name = cat_doc.get('name', str(c)) if cat_doc else str(c)
            cats[c_name] = cats.get(c_name, 0) + 1

print(f"Feeds interacted with: {seen_feeds}")
print("Categories seen:", cats)
