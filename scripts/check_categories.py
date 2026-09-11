#!/usr/bin/env python3
"""
Script to check all categories in the Prithu-DB MongoDB
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Database configuration
MONGO_URI = os.getenv("PRITHU_DB_URI", "mongodb+srv://prithuapp_db_user:eETUIeouSRU7Xipu@cluster0.x0vkq8e.mongodb.net/Prithu-DB?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = os.getenv("PRITHU_DB_NAME", "Prithu-DB")

print("=" * 70)
print("PRITHU - CATEGORIES ANALYZER")
print("=" * 70)

try:
    # Connect to MongoDB
    print("\n📡 Connecting to MongoDB Atlas...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    
    # Test connection
    client.admin.command('ping')
    print("✅ Connected successfully!")
    
    # Get database and collections
    db = client[DB_NAME]
    print(f"✅ Database: {DB_NAME}")
    
    # ================================================================
    # 1. CHECK CATEGORIES COLLECTION
    # ================================================================
    print("\n" + "=" * 70)
    print("1. CATEGORIES COLLECTION")
    print("=" * 70)
    
    categories_col = db["Categories"]
    total_categories = categories_col.count_documents({})
    print(f"\n📊 Total Categories: {total_categories}\n")
    
    if total_categories > 0:
        categories = list(categories_col.find({}).limit(100))
        
        print("Category List:")
        print("-" * 70)
        for idx, cat in enumerate(categories, 1):
            cat_id = cat.get("_id")
            cat_name = cat.get("name", "N/A")
            cat_desc = cat.get("description", "No description")
            cat_active = cat.get("isActive", cat.get("active", "N/A"))
            
            print(f"\n{idx}. ID: {cat_id}")
            print(f"   Name: {cat_name}")
            print(f"   Description: {cat_desc}")
            print(f"   Active: {cat_active}")
            
            # Print any other fields
            other_fields = {k: v for k, v in cat.items() if k not in ["_id", "name", "description", "isActive", "active"]}
            if other_fields:
                print(f"   Other Fields: {json.dumps(other_fields, indent=18, default=str)}")
    else:
        print("❌ No categories found in database!")
    
    # ================================================================
    # 2. CHECK BLOGS COLLECTION (for actual category usage)
    # ================================================================
    print("\n" + "=" * 70)
    print("2. BLOGS COLLECTION - CATEGORY USAGE")
    print("=" * 70)
    
    blogs_col = db["Blogs"]
    total_blogs = blogs_col.count_documents({})
    print(f"\n📊 Total Posts/Blogs: {total_blogs}\n")
    
    if total_blogs > 0:
        # Get unique categories from blogs
        unique_categories = blogs_col.distinct("category")
        print(f"📌 Unique Categories Used in Posts: {len(unique_categories)}\n")
        
        for idx, cat in enumerate(sorted(unique_categories), 1):
            cat_count = blogs_col.count_documents({"category": cat})
            print(f"{idx}. {cat}: {cat_count} posts")
    
    # ================================================================
    # 3. CHECK FEEDS COLLECTION (for category references)
    # ================================================================
    print("\n" + "=" * 70)
    print("3. FEEDS COLLECTION - CATEGORY REFERENCES")
    print("=" * 70)
    
    feeds_col = db["Feeds"]
    total_feeds = feeds_col.count_documents({})
    print(f"\n📊 Total Feeds: {total_feeds}\n")
    
    if total_feeds > 0:
        # Sample feed to see category structure
        sample_feed = feeds_col.find_one({})
        if sample_feed:
            print("📋 Sample Feed Structure:")
            print(f"   _id: {sample_feed.get('_id')}")
            print(f"   Category Field: {sample_feed.get('category', 'N/A')}")
            print(f"   Category Type: {type(sample_feed.get('category'))}")
            
            # Count by category
            unique_feed_cats = feeds_col.distinct("category")
            print(f"\n📌 Unique Categories in Feeds: {len(unique_feed_cats)}")
            
            for idx, cat in enumerate(sorted(str(c) for c in unique_feed_cats), 1):
                cat_count = feeds_col.count_documents({"category": cat})
                print(f"{idx}. {cat}: {cat_count} feeds")
    
    # ================================================================
    # 4. SUMMARY STATISTICS
    # ================================================================
    print("\n" + "=" * 70)
    print("4. SUMMARY STATISTICS")
    print("=" * 70)
    
    print(f"""
📊 Database Summary:
   - Total Categories: {total_categories}
   - Total Posts/Blogs: {total_blogs}
   - Total Feeds: {total_feeds}
   - Collections: {db.list_collection_names()}
""")
    
    print("\n✅ Analysis Complete!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    if 'client' in locals():
        client.close()
        print("\n📌 Connection closed.")
