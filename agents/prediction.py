from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import time
import asyncio
import os
import tensorflow as tf
import numpy as np

# Prediction Agent: Forecasts energy demand and production
class PredictionAgent(Agent):
    class PredictBehaviour(CyclicBehaviour):
        async def on_start(self):
            # Load the trained LSTM model when the agent starts
            project_dir = os.path.dirname(os.path.dirname(__file__))
            model_path = os.path.join(project_dir, "models", "energy_lstm.keras")
            self.model = tf.keras.models.load_model(model_path)

        async def run(self):
            print("[PredictionAgent] Waiting for input data...")
            await asyncio.sleep(5)
            msg = await self.receive(timeout=30)
            if msg:
                try:
                    # Decode the incoming message and extract the "house" data
                    data = json.loads(msg.body).get("house", {})
                except json.JSONDecodeError as e:
                    print(f"[PredictionAgent] JSON decode error: {e}")
                    return

                if not data:
                    print("[PredictionAgent] No data received")
                else:
                    print(f"[PredictionAgent] Received data: {data}")
                    try:
                        # Extract the 'test_sample' from the data
                        raw_test_sample = data.get("test_sample")
                        
                        # Ensure 'test_sample' exists and is properly formatted
                        if raw_test_sample and isinstance(raw_test_sample, list) and isinstance(raw_test_sample[0], list):
                            # Flatten the inner list to extract the values
                            extracted_data = [item[0] for item in raw_test_sample[0]]  # Flatten the list
                        else:
                            extracted_data = []
                            print("[PredictionAgent] Test sample is improperly formatted or empty")

                        # Convert the extracted data to a NumPy array and reshape it
                        if extracted_data:
                            test_sample = np.array(extracted_data).reshape(18, 1)
                        else:
                            print("[PredictionAgent] No valid test data extracted. Skipping prediction.")
                            return

                        # Ensure the shape is correct for prediction
                        if test_sample.shape != (18, 1):
                            print(f"[PredictionAgent] Incorrect data shape: {test_sample.shape}")
                            raise ValueError(f"Expected shape (18, 1), but received {test_sample.shape}")

                        # Reshape the data for the LSTM model input
                        test_sample = test_sample.reshape(1, 18, 1)

                        # Make a prediction using the trained model
                        predicted_demand, predicted_production = self.model.predict(test_sample)[0]

                        # Prepare the response message
                        response = Message(to="facilitating@localhost")
                        response.body = json.dumps({
                            "predicted_demand": float(predicted_demand),
                            "predicted_production": float(predicted_production)
                        })
                        await self.send(response)
                        print(f"[PredictionAgent] Sent prediction data to FacilitatingAgent: {response.body}")

                    except Exception as e:
                        # Handle any prediction or data processing errors
                        print(f"[PredictionAgent] Prediction Error: {e}")
                        print(f"[PredictionAgent] Data Shape: {test_sample.shape if 'test_sample' in locals() else 'N/A'}")
                        print(f"[PredictionAgent] Data: {data}")

    async def setup(self):
        print("[PredictionAgent] Started")
        self.add_behaviour(self.PredictBehaviour())
        self.web.start(hostname="localhost", port="9096")
