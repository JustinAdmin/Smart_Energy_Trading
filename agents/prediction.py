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
            # Get the project directory dynamically based on the script location
            project_dir = os.path.dirname(os.path.dirname(__file__))
            model_path = os.path.join(project_dir, "models","energy_lstm.keras")
            self.model = tf.keras.models.load_model(model_path)

        async def run(self):
            print("[PredictionAgent] Waiting for input data...")
            await asyncio.sleep(5)
            msg = await self.receive(timeout=30)
            if msg:
                try:
                    data = json.loads(msg.body).get("house")
                    if data is None:
                        print("[PredictionAgent] No data received")
                    else:
                        print(f"[PredictionAgent] Received data: {data}")
                        test_sample = data.get("test_sample")
                        
                        predicted_demand, predicted_production = self.model.predict(test_sample)[0]
                        
                        response = Message(to="facilitating@localhost")
                        response.body = json.dumps({
                            "predicted_demand": predicted_demand,
                            "predicted_production": predicted_production
                        })
                        await self.send(response)
                        print(f"[PredictionAgent] Sent prediction data to FacilitatingAgent: {response.body}")
                except Exception as e:
                    print(f"[PredictionAgent] Error: {e}")
                    print(f"[PredictionAgent] {msg}")
    
    async def setup(self):
        print("[PredictionAgent] Started")
        self.add_behaviour(self.PredictBehaviour())
        self.web.start(hostname="localhost", port="9096")