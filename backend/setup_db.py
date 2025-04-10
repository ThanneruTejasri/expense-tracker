# backend/setup_db.py
import sqlite3
import os

# Ensure the data directory exists
os.makedirs("data", exist_ok=True)

# Database connection
DATABASE_URL = "data/expenses.db"

def setup_database():
    print("Setting up database...")
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Create expenses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        description TEXT
    )
    """)
    
    # Create budgets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT UNIQUE NOT NULL,
        amount REAL NOT NULL
    )
    """)
    
    # Insert default categories if they don't exist
    categories = ["food", "transport", "entertainment", "household", "health", "other"]
    for category in categories:
        cursor.execute(
            "INSERT OR IGNORE INTO budgets (category, amount) VALUES (?, ?)",
            (category, 0.0)
        )
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print("Database setup complete!")

if __name__ == "__main__":
    setup_database()