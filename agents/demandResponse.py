from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
from datetime import datetime
import time
import asyncio
import os
import tensorflow as tf
import numpy as np


# Function to determine the current energy rate based on timestamp
def get_energy_rate(timestamp):
    # Convert timestamp to datetime object
    current_time = datetime.fromtimestamp(timestamp)

    # Ultra-low rate: 11 PM to 7 AM
    if current_time.hour >= 23 or current_time.hour < 7:
        return 0.028  # 2.8¢ per kWh

    # Weekend off-peak: 7 AM to 11 PM on weekends
    elif current_time.weekday() in [5, 6]:  # Saturday or Sunday
        if 7 <= current_time.hour < 23:
            return 0.076  # 7.6¢ per kWh
        else:
            return 0.028  # 2.8¢ per kWh (Ultra-low during off-peak hours)

    # Weekday mid-peak: 7 AM to 4 PM, 9 PM to 11 PM
    elif current_time.weekday() in [0, 1, 2, 3, 4]:  # Monday to Friday
        if 7 <= current_time.hour < 16 or 21 <= current_time.hour < 23:
            return 0.122  # 12.2¢ per kWh (Mid-peak)
        elif 16 <= current_time.hour < 21:
            return 0.284  # 28.4¢ per kWh (On-peak)
    
    return 0.028  # Default to ultra-low rate

# Demand Response Agent: Manages energy curtailment based on grid demand
class DemandResponseAgent(Agent):
    class DRBehaviour(CyclicBehaviour):
        async def on_start(self):
            # Load the trained LSTM model when the agent starts
            project_dir = os.path.dirname(os.path.dirname(__file__))
            model_path_demand = os.path.join(project_dir, "models", "lstm_cnn_demand_predictor.keras")
            model_path_supply = os.path.join(project_dir, "models", "lstm_cnn_supply_predictor.keras")
            self.model_demand = tf.keras.models.load_model(model_path_demand)
            self.model_supply = tf.keras.models.load_model(model_path_supply)
        
        async def run(self):
            print("[DemandResponseAgent] Waiting for grid data...")
            msg = await self.receive(timeout=30)
            await asyncio.sleep(5)
            if msg:
                try:
                    # Get grid data and timestamp
                    data = json.loads(msg.body).get("grid")
                    if data is None:
                        print("[DemandResponseAgent] No grid data received")
                    else:
                        print(f"[DemandResponseAgent] Received grid data")
                        test_sample_supply = np.array(data["test_sample_supply"])
                        test_sample_demand = np.array(data["test_sample_demand"])

                        predicted_demand = self.model_demand.predict(test_sample_demand)[0][0]
                        predicted_supply = self.model_supply.predict(test_sample_supply)[0][0]
                        
                        predicted_demand = predicted_demand * 4924.1 + 13673.1
                        predicted_supply = predicted_supply * 20667

                        timestamp = time.mktime(datetime.now().timetuple())
                        energy_rate = get_energy_rate(timestamp)
                        
                        curtailment = 0
                        if predicted_demand > predicted_supply:
                            curtailment = (predicted_demand - predicted_supply) * 0.1  # 10% curtailment
                        
                        response = Message(to="facilitating@localhost")
                        response.body = json.dumps({
                            "predicted_demand": float(predicted_demand),
                            "predicted_supply": float(predicted_supply),
                            "curtailment": curtailment,
                            "energy_rate": energy_rate,
                            "recommended_appliance_behaviour": [
                                "Reduce air conditioning usage", "Delay dishwasher cycle", "Limit electric heating between peak hours"
                            ]
                        })
                        
                        await self.send(response)
                        print(f"[DemandResponseAgent] Sent curtailment and energy rate to FacilitatingAgent: {response.body}")

                except Exception as e:
                    print(f"[DemandResponseAgent] Error: {e}")
                    print(f"[DemandResponseAgent] {msg}")
    
    async def setup(self):
        print("[DemandResponseAgent] Started")
        self.add_behaviour(self.DRBehaviour())
        self.web.start(hostname="localhost", port="9094")
