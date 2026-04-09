import sqlite3
import os

db_path = os.path.join('instance', 'perioguard.db')

def repair():
    if not os.path.exists(db_path):
        print(f"DATABASE NOT FOUND at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check for profile_pic
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'profile_pic' not in columns:
            print("REPAIR: Adding missing column: profile_pic")
            cursor.execute("ALTER TABLE users ADD COLUMN profile_pic VARCHAR(255)")
        else:
            print("INFO: Column profile_pic already exists.")

        if 'created_at' not in columns:
            print("REPAIR: Adding missing column: created_at")
            cursor.execute("ALTER TABLE users ADD COLUMN created_at DATETIME")
        else:
            print("INFO: Column created_at already exists.")

        conn.commit()
        print("SUCCESS: Database schema repaired successfully!")
    except Exception as e:
        print(f"ERROR during repair: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    repair()
