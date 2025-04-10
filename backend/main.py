# backend/main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import sqlite3
import os
from contextlib import contextmanager

# Initialize FastAPI app
app = FastAPI(title="Expense Tracker API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure the data directory exists
os.makedirs("data", exist_ok=True)

# Database connection
DATABASE_URL = "data/expenses.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Initialize database
def init_db():
    with get_db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT
        )
        """)
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT UNIQUE NOT NULL,
            amount REAL NOT NULL
        )
        """)
        
        # Insert default categories if they don't exist
        categories = ["food", "transport", "entertainment", "household", "health", "other"]
        for category in categories:
            conn.execute(
                "INSERT OR IGNORE INTO budgets (category, amount) VALUES (?, ?)",
                (category, 0.0)
            )
        
        conn.commit()

# Run database initialization
init_db()

# Pydantic models
class ExpenseBase(BaseModel):
    date: date
    amount: float
    category: str
    description: Optional[str] = None

class ExpenseCreate(ExpenseBase):
    pass

class Expense(ExpenseBase):
    id: int
    
    class Config:
        orm_mode = True

class BudgetBase(BaseModel):
    category: str
    amount: float

class BudgetCreate(BudgetBase):
    pass

class Budget(BudgetBase):
    id: int
    
    class Config:
        orm_mode = True

class MonthlyStats(BaseModel):
    category: str
    spent: float
    budget: float
    percentage: float

# API endpoints
@app.get("/")
def read_root():
    return {"message": "Welcome to the Expense Tracker API"}

@app.post("/expenses/", response_model=Expense, status_code=status.HTTP_201_CREATED)
def create_expense(expense: ExpenseCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO expenses (date, amount, category, description) VALUES (?, ?, ?, ?)",
            (expense.date.isoformat(), expense.amount, expense.category, expense.description)
        )
        conn.commit()
        
        # Get the created expense
        expense_id = cursor.lastrowid
        cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
        expense_data = dict(cursor.fetchone())
        
        # Check if budget is exceeded for this category in the current month
        month = expense.date.strftime("%Y-%m")
        cursor.execute("""
            SELECT SUM(amount) as total
            FROM expenses
            WHERE category = ? AND date LIKE ?
        """, (expense.category, f"{month}%"))
        result = cursor.fetchone()
        total_spent = result["total"] if result["total"] else 0
        
        cursor.execute("SELECT amount FROM budgets WHERE category = ?", (expense.category,))
        budget_row = cursor.fetchone()
        budget_amount = budget_row["amount"] if budget_row else 0
        
        budget_exceeded = False
        if budget_amount > 0 and total_spent > budget_amount:
            budget_exceeded = True
        
        # Convert date string back to date object for the response
        expense_data["date"] = date.fromisoformat(expense_data["date"])
        
        return {**expense_data, "budget_exceeded": budget_exceeded}

@app.get("/expenses/", response_model=List[Expense])
def list_expenses():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
        expenses = [dict(row) for row in cursor.fetchall()]
        
        # Convert date strings to date objects
        for expense in expenses:
            expense["date"] = date.fromisoformat(expense["date"])
        
        return expenses

@app.get("/expenses/{expense_id}", response_model=Expense)
def read_expense(expense_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
        expense = cursor.fetchone()
        
        if expense is None:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        expense_data = dict(expense)
        expense_data["date"] = date.fromisoformat(expense_data["date"])
        
        return expense_data

@app.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
        expense = cursor.fetchone()
        
        if expense is None:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        
        return None

@app.get("/budgets/", response_model=List[Budget])
def list_budgets():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM budgets ORDER BY category")
        return [dict(row) for row in cursor.fetchall()]

@app.put("/budgets/{category}", response_model=Budget)
def update_budget(category: str, budget: BudgetCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM budgets WHERE category = ?", (category,))
        existing_budget = cursor.fetchone()
        
        if existing_budget is None:
            raise HTTPException(status_code=404, detail="Budget category not found")
        
        cursor.execute(
            "UPDATE budgets SET amount = ? WHERE category = ?",
            (budget.amount, category)
        )
        conn.commit()
        
        cursor.execute("SELECT * FROM budgets WHERE category = ?", (category,))
        return dict(cursor.fetchone())

@app.get("/stats/monthly/{year}/{month}", response_model=List[MonthlyStats])
def get_monthly_stats(year: int, month: int):
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    
    month_str = f"{year:04d}-{month:02d}"
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all budget categories
        cursor.execute("SELECT category, amount FROM budgets ORDER BY category")
        budgets = {row["category"]: row["amount"] for row in cursor.fetchall()}
        
        # Get expenses for the selected month
        cursor.execute("""
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE date LIKE ?
            GROUP BY category
        """, (f"{month_str}%",))
        
        expenses = {row["category"]: row["total"] for row in cursor.fetchall()}
        
        # Prepare stats for all categories
        stats = []
        for category, budget_amount in budgets.items():
            spent = expenses.get(category, 0) or 0
            percentage = (spent / budget_amount * 100) if budget_amount > 0 else 0
            
            stats.append({
                "category": category,
                "spent": spent,
                "budget": budget_amount,
                "percentage": percentage
            })
        
        return stats

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)