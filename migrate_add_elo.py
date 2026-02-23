"""
Migration script to add elo_rating column to existing databases.

Run this script if you have an existing gallery.db file before the ELO update.
It will add the elo_rating column with default value 1500 to all existing records.

Usage:
    python migrate_add_elo.py
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
    
    if 'elo_rating' in columns:
        print("✓ elo_rating column already exists")
        conn.close()
        return
    
    print("Adding elo_rating column to media_file table...")
    
    try:
        # Add the column with default value
        cursor.execute("ALTER TABLE media_file ADD COLUMN elo_rating INTEGER DEFAULT 1500")
        conn.commit()
        
        # Count affected rows
        cursor.execute("SELECT COUNT(*) FROM media_file")
        count = cursor.fetchone()[0]
        
        print(f"✓ Successfully added elo_rating column")
        print(f"✓ Set default ELO rating (1500) for {count} existing media files")
        
    except sqlite3.Error as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("=== Gallery ELO Rating Migration ===")
    migrate()
    print("=== Migration complete ===")
