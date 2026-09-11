#!/usr/bin/env python3
"""
Simple script to list all categories
"""

import os
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://prithuapp_db_user:eETUIeouSRU7Xipu@cluster0.x0vkq8e.mongodb.net/Prithu-DB?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "Prithu-DB"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    db = client[DB_NAME]
    
    print("\n" + "=" * 80)
    print("PRITHU DATABASE - CATEGORIES LIST")
    print("=" * 80)
    
    categories_col = db["Categories"]
    total = categories_col.count_documents({})
    
    print(f"\n✅ Total Categories in Database: {total}\n")
    print("CATEGORY LIST:")
    print("-" * 80)
    
    categories = list(categories_col.find({}).sort("name", 1))
    
    for idx, cat in enumerate(categories, 1):
        cat_name = cat.get("name", "N/A")
        feed_count = len(cat.get("feedIds", []))
        print(f"{idx:3d}. {cat_name:30s} | Feeds: {feed_count}")
    
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"Error: {e}")

finally:
    if 'client' in locals():
        client.close()
