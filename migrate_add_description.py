"""
Migration script to add description column to existing databases.

Run this script if you have an existing gallery.db file before the description update.
It will add the description column (TEXT, nullable) to all existing records.

Usage:
    python migrate_add_description.py
"""

import sqlite3
import os

DB_PATH = 'instance/gallery.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        print("If this is a fresh install, you can ignore this script.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(media_file)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'description' in columns:
        print("✓ description column already exists")
        conn.close()
        return
    
    print("Adding description column to media_file table...")
    
    try:
        # Add the column (TEXT, nullable)
        cursor.execute("ALTER TABLE media_file ADD COLUMN description TEXT")
        conn.commit()
        
        # Count affected rows
        cursor.execute("SELECT COUNT(*) FROM media_file")
        count = cursor.fetchone()[0]
        
        print(f"✓ Successfully added description column")
        print(f"✓ Column added for {count} existing media files")
        print(f"  Note: All descriptions are initially NULL. You can:")
        print(f"    1. Edit descriptions via the Edit view")
        print(f"    2. Upload .txt files with matching names alongside new media")
        
    except sqlite3.Error as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("=== Gallery Description Field Migration ===")
    migrate()
    print("=== Migration complete ===")
