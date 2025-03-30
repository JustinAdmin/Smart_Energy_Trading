import streamlit as st
import sqlite3
import pandas as pd
import time
import datetime as dt

# --- Configuration ---
DB_NAME = "energy_data.db"
REFRESH_INTERVAL_SECONDS = 10
DEFAULT_HISTORY_MINUTES = 60

# --- NEW: GUIAgent Web Endpoint ---
GUI_AGENT_URL = f"http://localhost:{9099}" # Match port in GUIAgent
STRATEGY_ENDPOINT = f"{GUI_AGENT_URL}/set_strategy"

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
        elif table_name == "predictions": # <-- Added for predictions table
            cols = ['id', 'timestamp', 'predicted_demand', 'predicted_production']
        elif table_name == "demand_response_log":
            cols = ['id', 'timestamp', 'grid_predicted_demand', 'grid_predicted_supply', 'energy_rate_per_kwh', 'curtailment_kw']
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


# Initialize session state for strategy
if 'current_ui_strategy' not in st.session_state:
    st.session_state['current_ui_strategy'] = 'neutral' # Default on first load

conn = connect_db()

if conn:
    # --- Sidebar ---
    st.sidebar.header("⚙️ Controls")
    history_minutes = st.sidebar.slider("Time Window (Minutes)", 5, 1440, DEFAULT_HISTORY_MINUTES, 5)
    if st.sidebar.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()
        
     # --- NEW: Strategy Selection ---
    st.sidebar.subheader("Trading Strategy")
    strategy_options = ["conservative", "neutral", "aggressive"]
    # Use st.session_state to keep track of the selection
    selected_strategy = st.sidebar.radio(
        "Set Negotiation Agent Strategy:",
        options=strategy_options,
        index=strategy_options.index(st.session_state.current_ui_strategy), # Set default index based on state
        key="strategy_radio" # Assign a key for stability
    )

    # Check if the selection changed and update the agent if necessary
    if selected_strategy != st.session_state.current_ui_strategy:
        st.session_state.current_ui_strategy = selected_strategy # Update state first
        payload = json.dumps({"strategy": selected_strategy})
        headers = {'Content-Type': 'application/json'}
        status_placeholder = st.sidebar.empty() # To show status messages
        try:
            status_placeholder.info(f"Attempting to set strategy to {selected_strategy}...")
            response = requests.post(STRATEGY_ENDPOINT, data=payload, headers=headers, timeout=5) # Add timeout
            response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
            # Check response content if needed
            # response_data = response.json()
            status_placeholder.success(f"✅ Strategy set to {selected_strategy}!")
            time.sleep(1.5) # Briefly show success message
            status_placeholder.empty() # Clear message
        except requests.exceptions.ConnectionError:
             status_placeholder.error(f"❌ Connection Error: Could not reach GUIAgent at {GUI_AGENT_URL}. Is it running?")
        except requests.exceptions.Timeout:
            status_placeholder.error("❌ Timeout: GUIAgent did not respond.")
        except requests.exceptions.RequestException as e:
             status_placeholder.error(f"❌ Failed to set strategy: {e}")
             try:
                 # Try to get more detail from agent's response
                 error_detail = e.response.json().get("message", "No details")
                 st.sidebar.caption(f"Agent Error: {error_detail}")
             except: pass # Ignore errors getting details
    # --- END Strategy Selection ---

    # --- Fetch Data ---
    dR_log = fetch_recent_data(conn, "demand_response_log", history_minutes, 'timestamp', 'datetime')
    df_prod = fetch_recent_data(conn, "energy_production", history_minutes, 'timestamp', 'datetime')
    df_cons = fetch_recent_data(conn, "energy_consumption", history_minutes, 'timestamp', 'datetime')
    df_blockchain = fetch_recent_data(conn, "blockchain_log", history_minutes, 'timestamp')
    # --- Fetch Prediction Data ---
    df_preds = fetch_recent_data(conn, "predictions", history_minutes, 'timestamp', 'datetime') # Use datetime index
    df_summary_latest = fetch_recent_data(conn, "trade_summary", history_minutes * 2)
    if not df_summary_latest.empty: df_summary_latest = df_summary_latest.sort_values(by='timestamp', ascending=False).iloc[[0]]
    # --- KPIs ---
    st.header("📊 Live Metrics")
    # Expand to 4 columns for Predictions KPIs
    kpi_cols = st.columns(6)

    latest_bought = df_summary_latest['total_energy_bought_kwh'].iloc[0] if not df_summary_latest.empty else 0
    latest_sold = df_summary_latest['total_energy_sold_kwh'].iloc[0] if not df_summary_latest.empty else 0
    
    net_traded = latest_sold - latest_bought

    # --- Prediction KPIs ---
    latest_pred_prod = df_preds['predicted_production'].iloc[-1] if not df_preds.empty else 0
    latest_pred_demand = df_preds['predicted_demand'].iloc[-1] if not df_preds.empty else 0
    with kpi_cols[0]:
        st.metric(label="📈 Pred. Prod (kW)", value=f"{latest_pred_prod:.2f}")
    with kpi_cols[1]:
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

    with kpi_cols[2]: st.metric(label="💰 Wallet Balance (ETH)", value=f"{latest_balance_eth:.6f}")
    with kpi_cols[3]:
         st.markdown("**Negotiation Wallet**")
         st.text_area("Address (from log)", value=agent_address_display, disabled=True, label_visibility="collapsed")

    with kpi_cols[4]: st.metric(label="🛒 Energy Bought (kWh)", value=f"{latest_bought:.2f}", help="Total energy bought via auctions.")
    with kpi_cols[5]: st.metric(label="💰 Energy Sold (kWh)", value=f"{latest_sold:.2f}", help="Total energy sold via auctions.")
    st.markdown("---")

    # --- Energy Charts ---
    st.header("📈 Energy Trends (Actuals)")
    DR_kpi_cols = st.columns(4)

# cols = ['id', 'timestamp', 'grid_predicted_demand', 'grid_predicted_supply', 'energy_rate_per_kwh', 'curtailment_kw']
    # Energy KPIs
    latest_prod = dR_log['grid_predicted_demand'].iloc[-1] if not dR_log.empty else 0
    latest_cons = dR_log['grid_predicted_supply'].iloc[-1] if not dR_log.empty else 0
    net_power = latest_prod - latest_cons
    with DR_kpi_cols[0]: st.metric(label="☀️ grid demand (kW)", value=f"{latest_prod:.2f}")
    with DR_kpi_cols[1]: st.metric(label="🏠 Grid supply (kW)", value=f"{latest_cons:.2f}")
    with DR_kpi_cols[2]:
        delta_val = f"{abs(net_power):.2f}"
        delta_color = "normal" if net_power >= 0 else "inverse"
        delta_text = f"{delta_val} (Export)" if net_power >= 0 else f"{delta_val} (Import)"
        st.metric(label="⚡ Net Power (kW)", value=f"{net_power:.2f}", delta=delta_text, delta_color=delta_color)

#    chart_cols_actual = st.columns(2)
#    with chart_cols_actual[0]:
#        st.subheader("☀️ Actual Production")
#        if not df_prod.empty: st.line_chart(df_prod[['value']].rename(columns={'value': 'Prod (kW)'}), use_container_width=True)
#        else: st.warning("No recent production data.")
#    with chart_cols_actual[1]:
#        st.subheader("🏠 Actual Consumption")
#        if not df_cons.empty: st.line_chart(df_cons[['value']].rename(columns={'value': 'Cons (kW)'}), use_container_width=True)
#        else: st.warning("No recent consumption data.")

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