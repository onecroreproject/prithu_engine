import pymongo, os, datetime
from dotenv import load_dotenv
load_dotenv('.env')
db = pymongo.MongoClient(os.getenv('PRITHU_DB_URI'))[os.getenv('PRITHU_DB_NAME')]

# Check globally for any activity in the last 15 minutes
recent_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=15)
activities = list(db.UserActivities.find({'createdAt': {'$gte': recent_time}}).sort('createdAt', -1).limit(5))

print('Any global activities in last 15 mins:', len(activities))
for a in activities:
    print(f"User: {a.get('userId')}, Action: {a.get('actionType')}")
