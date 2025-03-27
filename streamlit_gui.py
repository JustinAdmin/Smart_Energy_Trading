import streamlit as st
import sqlite3
import pandas as pd
import time
import datetime as dt

# --- Configuration ---
DB_NAME = "energy_data.db"
REFRESH_INTERVAL_SECONDS = 10
DEFAULT_HISTORY_MINUTES = 60

# --- Database Functions ---
@st.cache_resource
def connect_db():
    try:
        return sqlite3.connect(f"file:{DB_NAME}?mode=ro", uri=True, check_same_thread=False)
    except sqlite3.OperationalError as e:
        st.error(f"Error connecting to database '{DB_NAME}': {e}")
        return None

@st.cache_data(ttl=REFRESH_INTERVAL_SECONDS)
def fetch_recent_data(_conn, table_name, minutes_back, parse_dates_col=None, index_col=None):
    if _conn is None: return pd.DataFrame()
    now_unix = time.time()
    start_time_unix = now_unix - (minutes_back * 60)
    try:
        query = f"SELECT * FROM {table_name} WHERE timestamp >= ? ORDER BY timestamp ASC"
        df = pd.read_sql_query(query, _conn, params=(start_time_unix,))
        if not df.empty and parse_dates_col and parse_dates_col in df.columns:
            df['datetime'] = pd.to_datetime(df[parse_dates_col], unit='s').dt.tz_localize(None)
            if index_col == 'datetime': df = df.set_index('datetime')
        return df
    except (pd.errors.DatabaseError, sqlite3.OperationalError) as e:
        st.warning(f"Could not fetch data from table '{table_name}'. It might be empty or missing. Error: {e}")
        # Return empty DataFrame with expected columns
        cols = []
        if table_name == "blockchain_log":
            cols = ['id', 'timestamp', 'agent_account', 'event_type', 'energy_kwh', 'price_eth', 'balance_eth', 'counterparty_address', 'status', 'auction_id']
        elif table_name in ["energy_production", "energy_consumption"]:
            cols = ['id', 'timestamp', 'value']
        elif table_name == "predictions": # <-- Added for predictions table
            cols = ['id', 'timestamp', 'predicted_demand', 'predicted_production']

        if cols:
            empty_df = pd.DataFrame(columns=[col for col in cols if col != 'datetime'])
            empty_df['datetime'] = pd.to_datetime([])
            if index_col == 'datetime': return empty_df.set_index('datetime')
            return empty_df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"An unexpected error occurred fetching {table_name}: {e}")
        return pd.DataFrame()

# --- Streamlit UI ---
st.set_page_config(layout="wide", page_title="Smart Home Energy Dashboard")
st.title("⚡ Smart Home Energy & Blockchain Dashboard")
st.caption(f"Visualizing data from `{DB_NAME}`. Refreshing approx. every {REFRESH_INTERVAL_SECONDS} seconds.")

conn = connect_db()

if conn:
    # --- Sidebar ---
    st.sidebar.header("⚙️ Controls")
    history_minutes = st.sidebar.slider("Time Window (Minutes)", 5, 1440, DEFAULT_HISTORY_MINUTES, 5)
    if st.sidebar.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

    # --- Fetch Data ---
    df_prod = fetch_recent_data(conn, "energy_production", history_minutes, 'timestamp', 'datetime')
    df_cons = fetch_recent_data(conn, "energy_consumption", history_minutes, 'timestamp', 'datetime')
    df_blockchain = fetch_recent_data(conn, "blockchain_log", history_minutes, 'timestamp')
    # --- Fetch Prediction Data ---
    df_preds = fetch_recent_data(conn, "predictions", history_minutes, 'timestamp', 'datetime') # Use datetime index

    # --- KPIs ---
    st.header("📊 Live Metrics")
    # Expand to 7 columns for Predictions KPIs
    kpi_cols = st.columns(7)

    # Energy KPIs
    latest_prod = df_prod['value'].iloc[-1] if not df_prod.empty else 0
    latest_cons = df_cons['value'].iloc[-1] if not df_cons.empty else 0
    net_power = latest_prod - latest_cons
    with kpi_cols[0]: st.metric(label="☀️ Actual Prod (kW)", value=f"{latest_prod:.2f}")
    with kpi_cols[1]: st.metric(label="🏠 Actual Cons (kW)", value=f"{latest_cons:.2f}")
    with kpi_cols[2]:
        delta_val = f"{abs(net_power):.2f}"
        delta_color = "normal" if net_power >= 0 else "inverse"
        delta_text = f"{delta_val} (Export)" if net_power >= 0 else f"{delta_val} (Import)"
        st.metric(label="⚡ Net Power (kW)", value=f"{net_power:.2f}", delta=delta_text, delta_color=delta_color)

    # --- Prediction KPIs ---
    latest_pred_prod = df_preds['predicted_production'].iloc[-1] if not df_preds.empty else 0
    latest_pred_demand = df_preds['predicted_demand'].iloc[-1] if not df_preds.empty else 0
    with kpi_cols[3]:
        st.metric(label="📈 Pred. Prod (kW)", value=f"{latest_pred_prod:.2f}")
    with kpi_cols[4]:
        st.metric(label="📉 Pred. Demand (kW)", value=f"{latest_pred_demand:.2f}")


    # Blockchain Wallet KPIs
    latest_balance_eth = 0.0
    agent_address_display = "Fetching..."
    if not df_blockchain.empty:
        latest_entry = df_blockchain.sort_values(by='timestamp', ascending=False).iloc[0]
        if pd.notna(latest_entry['balance_eth']): latest_balance_eth = latest_entry['balance_eth']
        if pd.notna(latest_entry['agent_account']): agent_address_display = latest_entry['agent_account']
        else: agent_address_display = "Address N/A"
    else: agent_address_display = "No logs yet..."

    with kpi_cols[5]: st.metric(label="💰 Wallet Balance (ETH)", value=f"{latest_balance_eth:.6f}")
    with kpi_cols[6]:
         st.markdown("**Negotiation Wallet**")
         st.text_area("Address (from log)", value=agent_address_display, disabled=True, label_visibility="collapsed")

    st.markdown("---")

    # --- Energy Charts ---
    st.header("📈 Energy Trends (Actuals)")
    chart_cols_actual = st.columns(2)
    with chart_cols_actual[0]:
        st.subheader("☀️ Actual Production")
        if not df_prod.empty: st.line_chart(df_prod[['value']].rename(columns={'value': 'Prod (kW)'}), use_container_width=True)
        else: st.warning("No recent production data.")
    with chart_cols_actual[1]:
        st.subheader("🏠 Actual Consumption")
        if not df_cons.empty: st.line_chart(df_cons[['value']].rename(columns={'value': 'Cons (kW)'}), use_container_width=True)
        else: st.warning("No recent consumption data.")

    # --- Prediction Charts ---
    st.header("🔮 Energy Forecasts")
    chart_cols_pred = st.columns(2)
    with chart_cols_pred[0]:
        st.subheader("📈 Predicted Production")
        if not df_preds.empty:
            st.line_chart(df_preds[['predicted_production']].rename(columns={'predicted_production': 'Pred Prod (kW)'}), use_container_width=True)
        else:
            st.warning("No recent production forecast data.")
    with chart_cols_pred[1]:
        st.subheader("📉 Predicted Demand")
        if not df_preds.empty:
            st.line_chart(df_preds[['predicted_demand']].rename(columns={'predicted_demand': 'Pred Demand (kW)'}), use_container_width=True)
        else:
            st.warning("No recent demand forecast data.")

     #--- Optional: Combined Chart (Actual vs Predicted) ---
        st.header("📊 Actual vs. Forecast")
        combined_chart_cols = st.columns(2)
        # Prepare dataframes for merging (ensure datetime index)
        df_prod_vs_pred = pd.merge(df_prod[['value']].rename(columns={'value':'Actual Prod (kW)'}),
                                   df_preds[['predicted_production']].rename(columns={'predicted_production':'Pred Prod (kW)'}),
                                   left_index=True, right_index=True, how='outer') # Use outer join
        df_cons_vs_pred = pd.merge(df_cons[['value']].rename(columns={'value':'Actual Cons (kW)'}),
                                   df_preds[['predicted_demand']].rename(columns={'predicted_demand':'Pred Demand (kW)'}),
                                   left_index=True, right_index=True, how='outer')
        with combined_chart_cols[0]:
             st.subheader("☀️ Production: Actual vs. Forecast")
             if not df_prod_vs_pred.empty:
                  st.line_chart(df_prod_vs_pred, use_container_width=True)
             else: st.warning("No data for production comparison.")
        with combined_chart_cols[1]:
             st.subheader("🏠 Consumption: Actual vs. Forecast")
             if not df_cons_vs_pred.empty:
                  st.line_chart(df_cons_vs_pred, use_container_width=True)
             else: st.warning("No data for consumption comparison.")


    st.markdown("---")

    # --- Blockchain Activity --- (Keep this section as is)
    st.header("🔗 Blockchain Auction Activity")
    if not df_blockchain.empty:
        st.subheader("💰 Wallet Balance Trend (ETH)")
        balance_chart_df = df_blockchain.dropna(subset=['balance_eth', 'datetime'])
        if not balance_chart_df.empty:
             balance_chart_df = balance_chart_df.set_index('datetime')[['balance_eth']]
             st.line_chart(balance_chart_df, use_container_width=True)
        else: st.warning("No balance data for trend chart.")

        st.subheader("📜 Recent Blockchain Log")
        display_cols = {
            'datetime': 'Timestamp', 'event_type': 'Event', 'energy_kwh': 'Energy (kWh)',
            'price_eth': 'Price (ETH)', 'balance_eth': 'New Balance (ETH)',
            'counterparty_address': 'Counterparty', 'status': 'Status', 'agent_account': 'Agent Acc'
        }
        blockchain_display_df = df_blockchain[list(display_cols.keys())].copy()
        blockchain_display_df.rename(columns=display_cols, inplace=True)
        st.dataframe(blockchain_display_df.sort_values(by='Timestamp', ascending=False), use_container_width=True, hide_index=True,
            column_config={
                 "Timestamp": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm:ss"),
                 "Energy (kWh)": st.column_config.NumberColumn(format="%.2f"),
                 "Price (ETH)": st.column_config.NumberColumn(format="%.6f"),
                 "New Balance (ETH)": st.column_config.NumberColumn(format="%.6f"),
                 # ... other column configs
            })
    else:
        st.info("No recent blockchain activity logged.")

    # --- Raw Data Explorer ---
    with st.expander("Raw Data Explorer"):
        st.subheader("Actual Production Data")
        st.dataframe(df_prod.sort_index(ascending=False), use_container_width=True)
        st.subheader("Actual Consumption Data")
        st.dataframe(df_cons.sort_index(ascending=False), use_container_width=True)
        # --- Add Predictions Table ---
        st.subheader("Predictions Data")
        st.dataframe(df_preds.sort_index(ascending=False), use_container_width=True)
        # --- Keep Blockchain Table ---
        st.subheader("Blockchain Log Data")
        st.dataframe(df_blockchain.sort_values(by='timestamp', ascending=False), use_container_width=True)

    # --- Auto-refresh ---
    time.sleep(REFRESH_INTERVAL_SECONDS)
    st.rerun()

else:
    st.error("Dashboard cannot load data: Database connection failed.")