from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
import json
import sqlite3
import time

class GUIAgent(Agent):
    def __init__(self, jid, password):
        super().__init__(jid, password)
        self.db_name = "energy_data.db"
        self.initialize_database()

    def initialize_database(self):
        """Creates tables for storing energy data if they do not exist."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        tables = {
            "energy_production": "CREATE TABLE IF NOT EXISTS energy_production (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, value REAL)",
            "energy_consumption": "CREATE TABLE IF NOT EXISTS energy_consumption (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, value REAL)",
            "energy_trade_strategy": "CREATE TABLE IF NOT EXISTS energy_trade_strategy (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, value TEXT)",
            "recommended_appliance_behaviours": "CREATE TABLE IF NOT EXISTS recommended_appliance_behaviours (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, value TEXT)"
        }

        for query in tables.values():
            cursor.execute(query)

        conn.commit()
        conn.close()

    def store_data(self, table, value):
        """Inserts data into the corresponding table."""
        timestamp = time.time()
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO {table} (timestamp, value) VALUES (?, ?)", (timestamp, value))
        conn.commit()
        conn.close()

    class guiBehaviour(CyclicBehaviour):
        async def run(self):
            print("[GUI] Waiting for data...")
            msg = await self.receive(timeout=5)  # Correct usage inside run()
            if msg:
                try:
                    data = json.loads(msg.body)
                    print(f"[GUI] Received data: {data}")

                    # Use self.agent to store data at the agent level
                    self.agent.store_data("energy_production", data["house"].get("energy_production", 0))
                    self.agent.store_data("energy_consumption", data["house"].get("energy_consumption", 0))
                    self.agent.store_data("energy_trade_strategy", data["negotiation"].get("energy_trade_strategy", "None"))
                    self.agent.store_data("recommended_appliance_behaviours", json.dumps(data["demandResponse"].get("recommended_appliance_behaviour", [])))

                except json.JSONDecodeError:
                    print(f"[GUI] Invalid message format: {msg.body}")

    async def setup(self):
        print("[GUI] Started")
        self.add_behaviour(self.guiBehaviour())  # Correctly starts the cyclic behavior
