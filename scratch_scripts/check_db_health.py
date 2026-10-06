import sys
sys.path.append('.')
from app.database.db_connection import get_db_manager

db = get_db_manager()

print("=== CHECKING FOR DUPLICATE / INCONSISTENT COLLECTIONS ===")
collections = db._db.list_collection_names()

groups_to_check = {
    "Users": ['User', 'Users', 'users'],
    "Categories": ['Categories', 'categories', 'UserCategorys'],
    "AnalyticsMetrics": ['AnalyticsMetrics', 'analyticsmetrics'],
    "ImageStats": ['ImageStats', 'imagestats'],
    "VideoStats": ['VideoStats', 'videostats'],
    "HiddenPosts": ['HiddenPosts', 'HiddenPost']
}

issues_found = 0

for group_name, col_list in groups_to_check.items():
    print(f"\nChecking group: {group_name}")
    for c in col_list:
        if c in collections:
            count = db._db[c].count_documents({})
            print(f" - Collection '{c}' exists with {count} records.")
            if count > 0:
                issues_found += 1
        else:
            print(f" - Collection '{c}' does not exist.")

print("\n=== CHECKING CATEGORY REFERENCES IN FEEDS ===")
# Check if Feeds are referencing valid Categories
feeds_with_cats = list(db._db.Feeds.find({"category": {"$exists": True, "$ne": []}}, {"category": 1}).limit(50))
invalid_refs = 0
for feed in feeds_with_cats:
    cats = feed.get("category", [])
    if cats:
        cat_id = cats[0]
        # Check if this category exists in Categories
        exists = db._db.Categories.find_one({"_id": cat_id})
        if not exists:
            invalid_refs += 1

if invalid_refs > 0:
    print(f"\nWARNING: Found {invalid_refs} feeds (out of 50 sampled) with invalid category IDs that don't exist in the 'Categories' collection!")
else:
    print("\nCategory references in Feeds look healthy.")
