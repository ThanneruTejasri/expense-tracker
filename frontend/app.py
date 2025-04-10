# frontend/app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import calendar
import json

# API base URL
API_URL = "http://localhost:8000"

# Set page configuration
st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to improve UI
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    .stAlert > div {
        padding: 0.5rem;
        margin-bottom: 1rem;
    }
    .success-alert {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    .warning-alert {
        background-color: #fff3cd;
        border-color: #ffeeba;
        color: #856404;
        padding: 1rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    .category-pill {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        margin-right: 0.5rem;
    }
    .food { background-color: #e6f7ff; color: #0070c0; }
    .transport { background-color: #e6ffe6; color: #009900; }
    .entertainment { background-color: #fff2e6; color: #ff9933; }
    .household { background-color: #f2e6ff; color: #9933ff; }
    .health { background-color: #ffe6e6; color: #ff3333; }
    .other { background-color: #f0f0f0; color: #666666; }
</style>
""", unsafe_allow_html=True)

# Functions to interact with the API
@st.cache_data(ttl=300)
def get_expenses():
    try:
        response = requests.get(f"{API_URL}/expenses/")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching expenses: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return []

@st.cache_data(ttl=300)
def get_budgets():
    try:
        response = requests.get(f"{API_URL}/budgets/")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching budgets: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return []

@st.cache_data(ttl=300)
def get_monthly_stats(year, month):
    try:
        response = requests.get(f"{API_URL}/stats/monthly/{year}/{month}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching monthly stats: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return []

def add_expense(expense_data):
    try:
        response = requests.post(f"{API_URL}/expenses/", json=expense_data)
        if response.status_code == 201:
            return response.json()
        else:
            st.error(f"Error adding expense: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return None

def update_budget(category, amount):
    try:
        response = requests.put(
            f"{API_URL}/budgets/{category}",
            json={"category": category, "amount": amount}
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error updating budget: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return None

def delete_expense(expense_id):
    try:
        response = requests.delete(f"{API_URL}/expenses/{expense_id}")
        if response.status_code == 204:
            return True
        else:
            st.error(f"Error deleting expense: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return False

# Title and navigation
st.title("💰 Personal Expense Tracker")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Add Expense", "Manage Budgets", "View Expenses"])

# Get the current month and year for default filtering
current_date = datetime.now()
current_year = current_date.year
current_month = current_date.month

# Dashboard page
if page == "Dashboard":
    st.header("Dashboard")
    
    # Month and year selector
    col1, col2 = st.columns(2)
    with col1:
        selected_month = st.selectbox(
            "Month", 
            range(1, 13), 
            format_func=lambda x: calendar.month_name[x],
            index=current_month - 1
        )
    
    with col2:
        selected_year = st.selectbox(
            "Year", 
            range(current_year - 5, current_year + 1),
            index=5  # Default to current year
        )
    
    # Get monthly statistics
    monthly_stats = get_monthly_stats(selected_year, selected_month)
    
    if not monthly_stats:
        st.info(f"No expense data available for {calendar.month_name[selected_month]} {selected_year}")
    else:
        # Convert to DataFrame for easier handling
        stats_df = pd.DataFrame(monthly_stats)
        
        # Calculate total spending vs total budget
        total_spent = stats_df["spent"].sum()
        total_budget = stats_df["budget"].sum()
        overall_percentage = (total_spent / total_budget * 100) if total_budget > 0 else 0
        
        # Summary metrics
        st.subheader("Monthly Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Spent", f"${total_spent:.2f}")
        
        with col2:
            st.metric("Total Budget", f"${total_budget:.2f}")
        
        with col3:
            delta = total_budget - total_spent
            delta_color = "normal" if delta >= 0 else "inverse"
            st.metric("Remaining Budget", f"${delta:.2f}", f"{delta:.2f}", delta_color=delta_color)
        
        # Progress bar for overall budget
        st.subheader("Overall Budget Usage")
        progress_color = "normal"
        if overall_percentage > 90:
            progress_color = "off"
        elif overall_percentage > 75:
            progress_color = "warning"
            
        st.progress(min(overall_percentage / 100, 1.0), text=f"{overall_percentage:.1f}% of budget used")
        
        # Budget usage by category
        st.subheader("Budget By Category")
        
        # Filter out categories with no budget or expenses
        filtered_stats = stats_df[(stats_df["budget"] > 0) | (stats_df["spent"] > 0)]
        
        if not filtered_stats.empty:
            # Create a bar chart comparing spending vs budget
            fig = go.Figure()
            
            # Add spent bars
            fig.add_trace(go.Bar(
                x=filtered_stats["category"],
                y=filtered_stats["spent"],
                name="Spent",
                marker_color="#36A2EB"
            ))
            
            # Add budget bars
            fig.add_trace(go.Bar(
                x=filtered_stats["category"],
                y=filtered_stats["budget"],
                name="Budget",
                marker_color="#FF6384"
            ))
            
            fig.update_layout(
                title="Spending vs Budget by Category",
                xaxis_title="Category",
                yaxis_title="Amount ($)",
                barmode="group",
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Spending breakdown pie chart
            fig = px.pie(
                filtered_stats,
                values="spent",
                names="category",
                title="Spending Breakdown",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No budget or expense data available for this month")

# Add Expense page
elif page == "Add Expense":
    st.header("Add New Expense")
    
    # Get budgets for reference and validation
    budgets = get_budgets()
    budgets_dict = {budget["category"]: budget["amount"] for budget in budgets}
    
    # Form for adding new expense
    with st.form("add_expense_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            expense_date = st.date_input("Date", value=datetime.now())
            expense_amount = st.number_input("Amount ($)", min_value=0.01, step=0.01, format="%.2f")
        
        with col2:
            expense_category = st.selectbox(
                "Category",
                options=[b["category"] for b in budgets],
                format_func=lambda x: x.capitalize()
            )
            expense_description = st.text_input("Description (optional)")
        
        submit_button = st.form_submit_button("Add Expense")
        
        if submit_button:
            expense_data = {
                "date": expense_date.isoformat(),
                "amount": expense_amount,
                "category": expense_category,
                "description": expense_description
            }
            
            response = add_expense(expense_data)
            
            if response:
                st.cache_data.clear()  # Clear cached data to refresh dashboard
                
                # Success message
                st.markdown(
                    f"""
                    <div class="success-alert">
                        Expense of ${expense_amount:.2f} added successfully!
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                # Check if budget exceeded and show warning
                if "budget_exceeded" in response and response["budget_exceeded"]:
                    budget_amount = budgets_dict.get(expense_category, 0)
                    
                    # Get current month's total for this category
                    current_month_str = datetime.now().strftime("%Y-%m")
                    monthly_stats = get_monthly_stats(
                        int(current_month_str.split("-")[0]), 
                        int(current_month_str.split("-")[1])
                    )
                    
                    category_stats = next(
                        (stat for stat in monthly_stats if stat["category"] == expense_category), 
                        {"spent": 0, "budget": 0}
                    )
                    
                    st.markdown(
                        f"""
                        <div class="warning-alert">
                            <strong>Budget Alert:</strong> You've exceeded your monthly budget for {expense_category.capitalize()}!<br>
                            Budget: ${budget_amount:.2f}<br>
                            Spent: ${category_stats["spent"]:.2f}<br>
                            Over budget by: ${(category_stats["spent"] - budget_amount):.2f}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
    
    # Show recent expenses
    st.subheader("Recent Expenses")
    expenses = get_expenses()
    
    if expenses:
        recent_expenses = expenses[:5]  # Show only 5 most recent
        
        for expense in recent_expenses:
            col1, col2, col3 = st.columns([2, 3, 1])
            
            with col1:
                st.write(f"**${expense['amount']:.2f}**")
                st.caption(expense["date"])
            
            with col2:
                category_class = expense["category"].lower()
                category_display = expense["category"].capitalize()
                
                st.markdown(
                    f"""
                    <div class="category-pill {category_class}">{category_display}</div>
                    {expense.get("description", "")}
                    """, 
                    unsafe_allow_html=True
                )
            
            with col3:
                if st.button("Delete", key=f"delete_{expense['id']}"):
                    if delete_expense(expense["id"]):
                        st.cache_data.clear()
                        st.experimental_rerun()
            
            st.divider()
    else:
        st.info("No expenses recorded yet")

# Manage Budgets page
elif page == "Manage Budgets":
    st.header("Manage Monthly Budgets")
    
    # Get current budgets
    budgets = get_budgets()
    
    if not budgets:
        st.warning("Could not load budget data")
    else:
        # Display form to update budgets
        st.write("Set your monthly budget limits for each expense category:")
        
        for budget in budgets:
            category = budget["category"]
            current_budget = budget["amount"]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                new_budget = st.number_input(
                    f"{category.capitalize()} Budget ($)",
                    min_value=0.0,
                    value=float(current_budget),
                    step=10.0,
                    format="%.2f",
                    key=f"budget_{category}"
                )
            
            with col2:
                if st.button("Update", key=f"update_{category}"):
                    if update_budget(category, new_budget):
                        st.cache_data.clear()
                        st.success(f"{category.capitalize()} budget updated to ${new_budget:.2f}")
        
        # Show current budgets visualization
        st.subheader("Current Budget Allocation")
        
        # Filter out zero budgets for visualization
        non_zero_budgets = [b for b in budgets if b["amount"] > 0]
        
        if non_zero_budgets:
            budget_df = pd.DataFrame(non_zero_budgets)
            
            fig = px.pie(
                budget_df,
                values="amount",
                names="category",
                title="Budget Allocation",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No budgets set yet. Use the form above to set your monthly budgets.")

# View Expenses page
elif page == "View Expenses":
    st.header("View & Filter Expenses")
    
    # Get all expenses
    expenses = get_expenses()
    
    if not expenses:
        st.info("No expenses recorded yet")
    else:
        # Convert to DataFrame for easier filtering
        df = pd.DataFrame(expenses)
        df["date"] = pd.to_datetime(df["date"])
        
        # Filtering options
        st.subheader("Filter Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date range filter
            date_range = st.date_input(
                "Date Range",
                value=(
                    df["date"].min().date(),
                    df["date"].max().date()
                ),
                max_value=datetime.now().date()
            )
        
        with col2:
            # Category filter
            categories = ["All"] + sorted(df["category"].unique().tolist())
            selected_category = st.selectbox("Category", categories)
        
        with col3:
            # Amount range filter
            min_amount = float(df["amount"].min())
            max_amount = float(df["amount"].max())
            
            amount_range = st.slider(
                "Amount Range ($)",
                min_value=min_amount,
                max_value=max_amount,
                value=(min_amount, max_amount),
                step=10.0
            )
        
        # Apply filters
        filtered_df = df.copy()
        
        # Date filter
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[
                (filtered_df["date"].dt.date >= start_date) &
                (filtered_df["date"].dt.date <= end_date)
            ]
        
        # Category filter
        if selected_category != "All":
            filtered_df = filtered_df[filtered_df["category"] == selected_category]
        
        # Amount filter
        filtered_df = filtered_df[
            (filtered_df["amount"] >= amount_range[0]) &
            (filtered_df["amount"] <= amount_range[1])
        ]
        
        # Display filtered expenses
        st.subheader(f"Expenses ({len(filtered_df)} results)")
        
        if filtered_df.empty:
            st.info("No expenses match your filter criteria")
        else:
            # Sort by date (most recent first)
            filtered_df = filtered_df.sort_values(by="date", ascending=False)
            
            # Calculate total for filtered expenses
            total_filtered = filtered_df["amount"].sum()
            st.metric("Total", f"${total_filtered:.2f}")
            
            # Display expenses in a table
            st.dataframe(
                filtered_df[["date", "amount", "category", "description"]].rename(
                    columns={
                        "date": "Date",
                        "amount": "Amount ($)",
                        "category": "Category",
                        "description": "Description"
                    }
                ),
                hide_index=True,
                use_container_width=True
            )
            
            # Download option
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Filtered Data",
                csv,
                "expense_data.csv",
                "text/csv",
                key="download-csv"
            )
            
            # Category breakdown for filtered expenses
            st.subheader("Category Breakdown")
            
            category_totals = filtered_df.groupby("category")["amount"].sum().reset_index()
            
            fig = px.bar(
                category_totals,
                x="category",
                y="amount",
                title="Expenses by Category",
                labels={"category": "Category", "amount": "Amount ($)"},
                color="category"
            )
            
            st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.caption("© 2025 Expense Tracker App | Made with Streamlit and FastAPI")