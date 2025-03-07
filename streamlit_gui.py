import streamlit as st
import sqlite3
import pandas as pd

DB_NAME = "energy_data.db"

def get_tables():
    """Fetches the list of tables in the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [table[0] for table in cursor.fetchall()]
    conn.close()
    return tables


def fetch_data(table_name):
    """Fetches data from the selected table."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

# Streamlit UI
st.title("SQLite Database Viewer")

tables = get_tables()

if tables:
    selected_table = st.selectbox("Select a table to view", tables)
    if st.button("Load Data"):
        df = fetch_data(selected_table)
        st.write(f"### Data from {selected_table}")
        st.dataframe(df)
else:
    st.write("No tables found in the database.")
