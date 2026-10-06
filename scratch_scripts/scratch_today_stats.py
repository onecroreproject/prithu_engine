import pymongo, os, datetime
from dotenv import load_dotenv
from bson.objectid import ObjectId

load_dotenv('.env')
db = pymongo.MongoClient(os.getenv('PRITHU_DB_URI'))[os.getenv('PRITHU_DB_NAME')]

uid = ObjectId('6923e91497388df4028311b1')
# Get start of today (UTC)
today = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

acts = list(db.UserActivities.find({'userId': uid, 'createdAt': {'$gte': today}}))
print(f"Total activities today: {len(acts)}")

likes = 0
shares_video = 0
shares_image = 0
views_video = 0
views_image = 0
cats = {}

for a in acts:
    action = a.get('actionType')
    target_id = a.get('targetId')
    
    if action == 'LIKE_POST':
        likes += 1
        
    feed = db.Feeds.find_one({'_id': target_id}) or db.feeds.find_one({'_id': target_id})
    post_type = 'unknown'
    c_name = 'unknown'
    
    if feed:
        post_type = feed.get('postType', feed.get('post_type', 'image')).lower()
        
        c = feed.get('category')
        if c:
            c = c[0] if isinstance(c, list) else c
            cat_doc = db.categories.find_one({'_id': c}) or db.Categories.find_one({'_id': c})
            c_name = cat_doc.get('name', str(c)) if cat_doc else str(c)
            cats[c_name] = cats.get(c_name, 0) + 1
            
    if action == 'SHARE_POST':
        if 'video' in post_type:
            shares_video += 1
        else:
            shares_image += 1
            
    if action in ['VIEW_FEED', 'WATCH_FEED', 'VIEW_PORTFOLIO', 'DOWNLOAD_POST', 'LIKE_POST']: # We'll count likes/downloads as seen since view event is missing
        if 'video' in post_type:
            views_video += 1
        else:
            views_image += 1

print(f"Likes today: {likes}")
print(f"Video Shares today: {shares_video}")
print(f"Image Shares today: {shares_image}")
print(f"Videos interacted with: {views_video}")
print(f"Images interacted with: {views_image}")
print("Categories today:", cats)
