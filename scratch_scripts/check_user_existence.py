import sys
sys.path.append('.')
from app.database.db_connection import get_db_manager

user_id = "google_TDubsbd6D8MGenHmT41H8AzVqNM2"
db = get_db_manager()

print(f"=== CHECKING USER ID EXISTENCE ===")
try:
    # Check if the user exists in the Users collection at all
    user = db.find_one('Users', {"_id": user_id})
    if not user:
        # Check by string match on 'uid' or something similar
        user = db.find_one('Users', {"uid": user_id})
    
    if user:
        print(f"User found in DB! Name: {user.get('displayName', user.get('name', 'Unknown'))}, Email: {user.get('email', 'None')}")
    else:
        print("User NOT found in the 'Users' collection with this exact ID.")
        
    print(f"\nTotal users in DB: {db._db.Users.count_documents({})}")
    
except Exception as e:
    print(f"Error checking user: {e}")
