#!/usr/bin/env python3
"""
Set up Vajra.Stream database
"""

import sqlite3
import os
from datetime import datetime


def create_database(db_path='vajra_stream.db'):
    """
    Create database with all necessary tables
    """
    # Remove existing database if present
    if os.path.exists(db_path):
        print(f"Database {db_path} already exists.")
        response = input("Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Keeping existing database.")
            return
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Creating tables...")
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_type TEXT,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            intention TEXT,
            focus_area TEXT,
            settings TEXT,
            notes TEXT
        )
    ''')
    
    # Intentions table
    cursor.execute('''
        CREATE TABLE intentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intention_text TEXT UNIQUE,
            created_at TIMESTAMP,
            times_used INTEGER DEFAULT 1,
            category TEXT,
            parent_intention_id INTEGER,
            FOREIGN KEY (parent_intention_id) REFERENCES intentions(id)
        )
    ''')
    
    # Generated content table
    cursor.execute('''
        CREATE TABLE generated_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type TEXT,
            content TEXT,
            created_at TIMESTAMP,
            intention_id INTEGER,
            quality_rating INTEGER,
            archived BOOLEAN DEFAULT 0,
            FOREIGN KEY (intention_id) REFERENCES intentions(id)
        )
    ''')
    
    # Healing history table
    cursor.execute('''
        CREATE TABLE healing_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            chakra TEXT,
            meridian TEXT,
            duration_minutes INTEGER,
            frequencies_used TEXT,
            subjective_result TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    ''')
    
    # Scheduled events table
    cursor.execute('''
        CREATE TABLE scheduled_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            target_datetime TIMESTAMP,
            location_lat REAL,
            location_lon REAL,
            intention TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP
        )
    ''')
    
    # User preferences table
    cursor.execute('''
        CREATE TABLE user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Insert default preferences
    defaults = [
        ('hardware_level', '2'),
        ('default_duration', '300'),
        ('audio_device', 'default'),
        ('sample_rate', '44100'),
    ]
    
    cursor.executemany(
        'INSERT INTO user_preferences (key, value) VALUES (?, ?)',
        defaults
    )
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Database created: {db_path}")
    print("✓ All tables initialized")
    print("✓ Default preferences set")
    print("\nDatabase ready for use! 🙏")


if __name__ == "__main__":
    create_database()
