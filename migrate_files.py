#!/usr/bin/env python3
"""
Migration script to organize existing files into subfolders
Run this once to migrate existing uploads to the new folder structure
"""
import os
import shutil
import sqlite3
from pathlib import Path

def get_file_subfolder(filename):
    """Get subfolder based on first 2 characters of filename"""
    return filename[:2] if len(filename) >= 2 else '00'

def migrate_files():
    """Migrate existing files to subfolder structure"""
    
    uploads_dir = 'uploads'
    database_path = 'instance/gallery.db'
    
    if not os.path.exists(uploads_dir):
        print("No uploads directory found. Nothing to migrate.")
        return
    
    if not os.path.exists(database_path):
        print("No database found. Nothing to migrate.")
        return
    
    print("Starting file migration to subfolder structure...")
    
    # Connect to database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    try:
        # Get all files from database
        cursor.execute("SELECT id, filename FROM media_file")
        files = cursor.fetchall()
        
        migrated_count = 0
        
        for file_id, filename in files:
            old_path = os.path.join(uploads_dir, filename)
            
            # Skip if file doesn't exist or is already in a subfolder
            if not os.path.exists(old_path) or '/' in filename or '\\' in filename:
                continue
            
            # Create subfolder
            subfolder = get_file_subfolder(filename)
            subfolder_path = os.path.join(uploads_dir, subfolder)
            os.makedirs(subfolder_path, exist_ok=True)
            
            # Move file
            new_path = os.path.join(subfolder_path, filename)
            shutil.move(old_path, new_path)
            
            # Update database with new relative path
            new_filename = f"{subfolder}/{filename}"
            cursor.execute("UPDATE media_file SET filename = ? WHERE id = ?", (new_filename, file_id))
            
            migrated_count += 1
            print(f"Migrated: {filename} -> {new_filename}")
        
        # Commit changes
        conn.commit()
        
        print(f"\nMigration completed! Migrated {migrated_count} files.")
        
        if migrated_count > 0:
            print("\nSubfolder structure created:")
            for item in os.listdir(uploads_dir):
                item_path = os.path.join(uploads_dir, item)
                if os.path.isdir(item_path):
                    file_count = len([f for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f))])
                    print(f"  {item}/: {file_count} files")
    
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_files()
