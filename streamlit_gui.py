import streamlit as st
import sqlite3
import pandas as pd
import time
import datetime as dt

# --- Configuration ---
DB_NAME = "energy_data.db"
REFRESH_INTERVAL_SECONDS = 10 # How often to check for new data
DEFAULT_HISTORY_MINUTES = 60 # How many minutes of data to show by default

# --- REMOVED HARDCODED ADDRESS ---
# The Negotiation Agent's address will now be fetched dynamically
# from the 'blockchain_log' table in the database.
# NEGOTIATION_AGENT_ADDRESS = "0x..." # <-- NO LONGER NEEDED

# --- Database Functions ---

@st.cache_resource
def connect_db():
    """Connects to the SQLite database."""
    try:
        return sqlite3.connect(f"file:{DB_NAME}?mode=ro", uri=True, check_same_thread=False)
    except sqlite3.OperationalError as e:
        st.error(f"Error connecting to database '{DB_NAME}': {e}")
        st.error("Ensure agents are running and have created/populated the database file.")
        return None

@st.cache_data(ttl=REFRESH_INTERVAL_SECONDS)
def fetch_recent_data(_conn, table_name, minutes_back, parse_dates_col=None, index_col=None):
    """Fetches data from the selected table within the last N minutes."""
    if _conn is None:
        return pd.DataFrame()

    now_unix = time.time()
    start_time_unix = now_unix - (minutes_back * 60)

    try:
        query = f"SELECT * FROM {table_name} WHERE timestamp >= ? ORDER BY timestamp ASC"
        df = pd.read_sql_query(query, _conn, params=(start_time_unix,))

        if not df.empty and parse_dates_col and parse_dates_col in df.columns:
            df['datetime'] = pd.to_datetime(df[parse_dates_col], unit='s').dt.tz_localize(None)
            if index_col == 'datetime':
                 df = df.set_index('datetime')
        return df

    except (pd.errors.DatabaseError, sqlite3.OperationalError) as e:
        st.warning(f"Could not fetch data from table '{table_name}'. It might be empty or missing. Error: {e}")
        # Return empty DataFrame with expected columns
        if table_name == "blockchain_log":
             cols = ['id', 'timestamp', 'agent_account', 'event_type', 'energy_kwh', 'price_eth', 'balance_eth', 'counterparty_address', 'status', 'auction_id', 'datetime']
             empty_df = pd.DataFrame(columns=[col for col in cols if col != 'datetime'])
             empty_df['datetime'] = pd.to_datetime([])
             if index_col == 'datetime': return empty_df.set_index('datetime')
             return empty_df
        elif table_name in ["energy_production", "energy_consumption"]:
             empty_df = pd.DataFrame(columns=['id', 'timestamp', 'value'])
             empty_df['datetime'] = pd.to_datetime([])
             if index_col == 'datetime': return empty_df.set_index('datetime')[['value']]
             return empty_df
        else:
             return pd.DataFrame()
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching data from {table_name}: {e}")
        return pd.DataFrame()


# --- Streamlit UI ---

st.set_page_config(layout="wide", page_title="Smart Home Energy Dashboard")
st.title("⚡ Smart Home Energy & Blockchain Dashboard")
st.caption(f"Visualizing data from `{DB_NAME}`. Refreshing approx. every {REFRESH_INTERVAL_SECONDS} seconds.")

conn = connect_db()

if conn:
    # --- Sidebar Controls ---
    st.sidebar.header("⚙️ Controls")
    history_minutes = st.sidebar.slider(
        "Time Window (Minutes)", 5, 1440, DEFAULT_HISTORY_MINUTES, 5,
        help="How many minutes of recent data to display."
    )
    if st.sidebar.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

    # --- Fetch Data ---
    df_prod = fetch_recent_data(conn, "energy_production", history_minutes, parse_dates_col='timestamp', index_col='datetime')
    df_cons = fetch_recent_data(conn, "energy_consumption", history_minutes, parse_dates_col='timestamp', index_col='datetime')
    df_blockchain = fetch_recent_data(conn, "blockchain_log", history_minutes, parse_dates_col='timestamp', index_col=None)

    # --- Main Dashboard Area ---

    # Row 1: KPIs
    st.header("📊 Live Metrics")
    kpi_cols = st.columns(5)

    # Energy KPIs (same as before)
    latest_prod = df_prod['value'].iloc[-1] if not df_prod.empty else 0
    latest_cons = df_cons['value'].iloc[-1] if not df_cons.empty else 0
    net_power = latest_prod - latest_cons
    with kpi_cols[0]: st.metric(label="☀️ Latest Production (kW)", value=f"{latest_prod:.2f}")
    with kpi_cols[1]: st.metric(label="🏠 Latest Consumption (kW)", value=f"{latest_cons:.2f}")
    with kpi_cols[2]:
        delta_val = f"{abs(net_power):.2f}"
        delta_color = "normal" if net_power >= 0 else "inverse"
        delta_text = f"{delta_val} (Exporting)" if net_power >= 0 else f"{delta_val} (Importing)"
        st.metric(label="⚡ Net Power (kW)", value=f"{net_power:.2f}", delta=delta_text, delta_color=delta_color)

    # --- Dynamic Blockchain Wallet KPIs ---
    latest_balance_eth = 0.0
    agent_address_display = "Fetching..." # Default display text

    if not df_blockchain.empty:
        # Find the most recent log entry
        latest_blockchain_entry = df_blockchain.sort_values(by='timestamp', ascending=False).iloc[0]

        # Get balance from the latest log entry
        if pd.notna(latest_blockchain_entry['balance_eth']):
            latest_balance_eth = latest_blockchain_entry['balance_eth']

        # *** Get address directly from the latest log entry ***
        if pd.notna(latest_blockchain_entry['agent_account']):
            agent_address_display = latest_blockchain_entry['agent_account']
        else:
            # This case should be rare if the agent logs correctly on startup
            agent_address_display = "Address not logged"

    else:
        # If no blockchain logs are found in the time window yet
        agent_address_display = "No logs yet..."

    # Display Wallet Balance Metric
    with kpi_cols[3]:
         st.metric(label="💰 Wallet Balance (ETH)", value=f"{latest_balance_eth:.6f}")

    # Display Dynamically Fetched Wallet Address
    with kpi_cols[4]:
         st.markdown("**Negotiation Agent Wallet**")
         st.text_area("Address (from log)", value=agent_address_display, disabled=True, label_visibility="collapsed")
         # Removed the warning about address mismatch

    st.markdown("---")

    # Row 2: Energy Charts (same as before)
    st.header("📈 Energy Trends")
    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.subheader("☀️ Energy Production")
        if not df_prod.empty: st.line_chart(df_prod[['value']].rename(columns={'value': 'Production (kW)'}), use_container_width=True)
        else: st.warning("No recent production data available.")
    with chart_cols[1]:
        st.subheader("🏠 Energy Consumption")
        if not df_cons.empty: st.line_chart(df_cons[['value']].rename(columns={'value': 'Consumption (kW)'}), use_container_width=True)
        else: st.warning("No recent consumption data available.")

    st.markdown("---")

    # Row 3: Blockchain Activity Display (same as before, but "Agent Acc" column now shows dynamic address)
    st.header("🔗 Blockchain Auction Activity")
    if not df_blockchain.empty:
        # Wallet Balance Trend Chart
        st.subheader("💰 Wallet Balance Trend (ETH)")
        balance_chart_df = df_blockchain.dropna(subset=['balance_eth', 'datetime'])
        if not balance_chart_df.empty:
             balance_chart_df = balance_chart_df.set_index('datetime')[['balance_eth']]
             st.line_chart(balance_chart_df, use_container_width=True)
        else: st.warning("No balance data available for trend chart.")

        # Recent Blockchain Log Table
        st.subheader("📜 Recent Blockchain Log")
        display_cols = {
            'datetime': 'Timestamp', 'event_type': 'Event', 'energy_kwh': 'Energy (kWh)',
            'price_eth': 'Price (ETH)', 'balance_eth': 'New Balance (ETH)',
            'counterparty_address': 'Counterparty', 'status': 'Status',
            'agent_account': 'Agent Acc' # This column now reliably shows the dynamic address
        }
        blockchain_display_df = df_blockchain[list(display_cols.keys())].copy()
        blockchain_display_df.rename(columns=display_cols, inplace=True)

        st.dataframe(
            blockchain_display_df.sort_values(by='Timestamp', ascending=False),
            use_container_width=True, hide_index=True,
            column_config={
                 "Timestamp": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm:ss"),
                 "Energy (kWh)": st.column_config.NumberColumn(format="%.2f"),
                 "Price (ETH)": st.column_config.NumberColumn(format="%.6f"),
                 "New Balance (ETH)": st.column_config.NumberColumn(format="%.6f"),
                 "Counterparty": st.column_config.TextColumn(width="small", help="Blockchain address of the other party in the transaction, if applicable."),
                 "Agent Acc": st.column_config.TextColumn(width="small", help="The blockchain address of the agent performing the action."),
                 "Status": st.column_config.TextColumn(width="small")
            }
        )
    else:
        st.info("No recent blockchain activity logged in the selected time window.")

    # Raw Data Explorer (same as before)
    with st.expander("Raw Data Explorer"):
        st.subheader("Energy Production Data (Recent)")
        st.dataframe(df_prod.sort_index(ascending=False), use_container_width=True)
        st.subheader("Energy Consumption Data (Recent)")
        st.dataframe(df_cons.sort_index(ascending=False), use_container_width=True)
        st.subheader("Blockchain Log Data (Recent)")
        st.dataframe(df_blockchain.sort_values(by='timestamp', ascending=False), use_container_width=True)

    # Auto-refresh
    time.sleep(REFRESH_INTERVAL_SECONDS)
    st.rerun() # Just call rerun directly

else:
    st.error("Dashboard cannot load data because the database connection failed.")