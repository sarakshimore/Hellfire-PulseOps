import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

RDS_USER = os.getenv("RDS_USER", "postgres")
RDS_PASSWORD = os.getenv("RDS_PASSWORD", "")
RDS_HOST = os.getenv("RDS_HOST", "localhost")
RDS_PORT = os.getenv("RDS_PORT", "5432")
RDS_DB_NAME = os.getenv("RDS_DB_NAME", "hellfire_pulseops")

def main():
    try:
        print(f"Connecting to {RDS_HOST}...")
        conn = psycopg2.connect(
            host=RDS_HOST,
            database=RDS_DB_NAME,
            user=RDS_USER,
            password=RDS_PASSWORD,
            port=RDS_PORT
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Add the missing columns to hospitals table
        columns = [
            ("city", "VARCHAR(100)"),
            ("state", "VARCHAR(100)"),
            ("pincode", "VARCHAR(20)"),
            ("number_of_beds", "INTEGER DEFAULT 0"),
            ("icu_beds", "INTEGER DEFAULT 0"),
            ("emergency_beds", "INTEGER DEFAULT 0"),
            ("operating_rooms", "INTEGER DEFAULT 0")
        ]
        
        for col, col_type in columns:
            try:
                cur.execute(f"ALTER TABLE hospitals ADD COLUMN {col} {col_type};")
                print(f"Added column: {col}")
            except psycopg2.errors.DuplicateColumn:
                print(f"Column {col} already exists, skipping.")
                
        cur.close()
        conn.close()
        print("Database schema successfully updated!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
