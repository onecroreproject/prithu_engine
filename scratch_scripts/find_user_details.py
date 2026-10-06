import sys
sys.path.append('.')
from app.database.db_connection import get_db_manager

db = get_db_manager()

emails = ["ram.rrr.95@gmail.com"]
names = ["Ram Srinivash", "RsNivashRajendran"]

print("=== SEARCHING FOR USER ===")
try:
    for collection_name in ['Users', 'User', 'users']:
        print(f"\nChecking collection '{collection_name}'...")
        
        # Build query
        query = {
            "$or": [
                {"email": {"$in": emails}},
                {"email": {"$regex": "ram.rrr.95", "$options": "i"}},
                {"name": {"$regex": "Ram Srinivash|RsNivashRajendran", "$options": "i"}},
                {"displayName": {"$regex": "Ram Srinivash|RsNivashRajendran", "$options": "i"}},
                {"username": {"$regex": "Ram Srinivash|RsNivashRajendran", "$options": "i"}}
            ]
        }
        
        cursor = db._db[collection_name].find(query)
        found = False
        for user in cursor:
            found = True
            print(f"Match found!")
            print(f" - ID (_id): {user.get('_id')}")
            print(f" - UID (uid): {user.get('uid')}")
            print(f" - Name: {user.get('name') or user.get('displayName')}")
            print(f" - Email: {user.get('email')}")
            
        if not found:
            print("No matches found.")
            
except Exception as e:
    print(f"Error finding user: {e}")
