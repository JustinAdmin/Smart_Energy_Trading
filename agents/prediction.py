from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import time
import asyncio
import os
import tensorflow as tf
import numpy as np
import sqlite3 # Import sqlite3

# --- Database Configuration ---
DB_NAME = "energy_data.db" # Use the same DB name as other agents

def initialize_predictions_table(db_name):
    """Creates the predictions table if it doesn't exist."""
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,          -- Unix timestamp when prediction was made
                predicted_demand REAL,   -- Forecasted demand value
                predicted_production REAL -- Forecasted production value
            )
        """)
        conn.commit()
        conn.close()
        print("[PredictionAgent] Predictions log table initialized.")
    except Exception as e:
         print(f"[PredictionAgent] ERROR initializing predictions table: {e}")

def log_prediction(db_name, timestamp, demand, production):
    """Logs prediction data to the database."""
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO predictions (timestamp, predicted_demand, predicted_production)
            VALUES (?, ?, ?)
        """, (timestamp, float(demand), float(production))) # Ensure values are float
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[PredictionAgent] ERROR logging prediction to database: {e}")


# Prediction Agent: Forecasts energy demand and production
class PredictionAgent(Agent):
    class PredictBehaviour(CyclicBehaviour):
        async def on_start(self):
            # Load the trained LSTM model when the agent starts
            try:
                project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                model_path = os.path.join(project_dir, "models", "energy_lstm.keras")
                if not os.path.exists(model_path):
                     print(f"[PredictionAgent] ERROR: Model file not found at {model_path}")
                     # Consider stopping the agent or preventing behavior start
                     # await self.agent.stop() # Example: Stop agent if model missing
                     return
                self.model = tf.keras.models.load_model(model_path)
                print("[PredictionAgent] LSTM Model loaded successfully.")
            except Exception as e:
                 print(f"[PredictionAgent] ERROR loading LSTM model: {e}")
                 # Handle error appropriately - maybe agent shouldn't run?

        async def run(self):
            if not hasattr(self, 'model'):
                 print("[PredictionAgent] Model not loaded, skipping prediction cycle.")
                 await asyncio.sleep(10) # Wait longer if model failed to load
                 return

            print("[PredictionAgent] Waiting for input data...")
            # Consider a shorter sleep if you expect data frequently
            await asyncio.sleep(5)
            msg = await self.receive(timeout=15) # Slightly shorter timeout?
            if msg:
                try:
                    # Assuming message body structure: {"house": {"test_sample": [...]}}
                    data = json.loads(msg.body).get("house", {})
                except json.JSONDecodeError as e:
                    print(f"[PredictionAgent] JSON decode error: {e}")
                    return # Skip this cycle on bad message format

                if not data or "test_sample" not in data:
                    # Adjusted condition to check specifically for test_sample
                    print("[PredictionAgent] No valid 'test_sample' data received in message.")
                else:
                    print(f"[PredictionAgent] Received data containing 'test_sample'")
                    try:
                        # Extract the 'test_sample' from the data
                        raw_test_sample = data.get("test_sample")

                        # --- Data Validation and Processing ---
                        # Assuming test_sample is like [[[val1], [val2], ...]] based on previous code
                        if isinstance(raw_test_sample, list) and raw_test_sample and isinstance(raw_test_sample[0], list):
                            # Flatten the inner list structure: [[[v1],[v2]]] -> [v1, v2]
                             extracted_data = [item[0] for item in raw_test_sample[0] if isinstance(item, list) and len(item)>0]
                        else:
                            extracted_data = []
                            print("[PredictionAgent] 'test_sample' is improperly formatted or empty.")

                        if not extracted_data or len(extracted_data) != 18: # Check length explicitly
                            print(f"[PredictionAgent] Invalid data extracted or incorrect length ({len(extracted_data)} != 18). Skipping prediction.")
                            return

                        # Convert and reshape for the model
                        test_sample_np = np.array(extracted_data).astype(np.float32) # Ensure float type
                        # Reshape directly to model input shape (1 batch, 18 timesteps, 1 feature)
                        test_sample_input = test_sample_np.reshape(1, 18, 1)

                        # --- Make Prediction ---
                        prediction_result = self.model.predict(test_sample_input)
                        # Assuming model output is [[predicted_demand, predicted_production]]
                        predicted_demand = prediction_result[0][0]
                        predicted_production = prediction_result[0][1]
                        print(f"[PredictionAgent] Prediction successful: Demand={predicted_demand:.4f}, Production={predicted_production:.4f}")


                        # --- Log Prediction to Database ---
                        current_timestamp = time.time()
                        log_prediction(DB_NAME, current_timestamp, predicted_demand, predicted_production)
                        print("[PredictionAgent] Prediction logged to database.")


                        # --- Send Prediction Message (to FacilitatingAgent) ---
                        response = Message(to="facilitating@localhost")
                        response.body = json.dumps({
                            "predicted_demand": float(predicted_demand),
                            "predicted_production": float(predicted_production)
                        })
                        await self.send(response)
                        print(f"[PredictionAgent] Sent prediction data to FacilitatingAgent: {response.body}")

                    except ValueError as ve:
                        # Catch specific errors like reshape issues
                        print(f"[PredictionAgent] Data Processing Error: {ve}")
                        # Log relevant info if helpful
                        print(f"[PredictionAgent] Raw Sample causing error: {raw_test_sample}")
                    except Exception as e:
                        # Handle other prediction or data processing errors
                        print(f"[PredictionAgent] Prediction/Processing Error: {e}")
                        # Avoid printing potentially large data structures in production logs
                        # print(f"[PredictionAgent] Data: {data}") # Maybe only log on debug level

            else:
                print("[PredictionAgent] No message received in timeout period.")
            # Add a small delay even if no message, prevents tight loop if always timing out
            await asyncio.sleep(1)


    async def setup(self):
        print("[PredictionAgent] Started")
        # Initialize DB Table during setup
        initialize_predictions_table(DB_NAME)
        # Add behavior
        predict_b = self.PredictBehaviour()
        self.add_behaviour(predict_b)
        # Start web server if needed (keep if used)
        try:
            self.web.start(hostname="localhost", port="9096")
            print("[PredictionAgent] Web server started on port 9096.")
        except Exception as e:
            print(f"[PredictionAgent] Failed to start web server: {e}")