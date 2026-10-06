import pymongo, os
from dotenv import load_dotenv
load_dotenv('.env')
db = pymongo.MongoClient(os.getenv('PRITHU_DB_URI'))[os.getenv('PRITHU_DB_NAME')]

email = 'ram.rrr.95@gmail.com'
user = db.users.find_one({'email': email}) or db.Users.find_one({'email': email}) or db.User.find_one({'email': email})

if user:
    print('User Details Found for', email)
    for k, v in user.items():
        if k not in ['password', 'hash', 'salt', 'fcmToken', 'tokens']:
            print(f'{k}: {str(v)}')
    
    user_id = user.get('_id')
    # Also fetch recent activity for this user
    print('\n--- Recent Activities ---')
    activities = list(db.UserActivities.find({'userId': user_id}).sort('createdAt', -1).limit(5))
    if activities:
        for a in activities:
            print(f"Action: {a.get('actionType')}, Date: {a.get('createdAt')}")
    else:
        print('No recent activities found for this user.')
else:
    print('User not found with email:', email)
