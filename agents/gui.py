from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
import json
import sqlite3
import time
import asyncio

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
            "energy_consumption": "CREATE TABLE IF NOT EXISTS energy_consumption (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, value REAL)"
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
            msg = await self.receive(timeout=30)
            await asyncio.sleep(5)
            if msg:
                try:
                    data = json.loads(msg.body)
                    if data["house"] is None:
                        print(f"[GUI] Missing data: {data}")
                    else:
                        print(f"[GUI] Received data: {data}")

                        # Use self.agent to store data at the agent level
                        self.agent.store_data("energy_production", data["house"].get("energy_production", 0))
                        self.agent.store_data("energy_consumption", data["house"].get("energy_consumption", 0))

                except Exception as e:
                    print(f"[GUI] Error: {e}")
                    print(f"[GUI] {msg}")

    async def setup(self):
        print("[GUI] Started")
        self.add_behaviour(self.guiBehaviour())  # Correctly starts the cyclic behavior
