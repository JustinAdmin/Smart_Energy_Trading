from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import os
import asyncio
import numpy as np
import random
import math

# Function to create pretend temperature
def temperature_model(time_step: int):
    """
    Simulates temperature variation based on a time step.
    :param time_step: Integer representing time (e.g., hours, days, etc.)
    :return: Simulated temperature value.
    """
    base_temp = 20  # Base temperature in degrees Celsius
    amplitude = 10  # Maximum deviation from the base temp
    period = 24  # Period of temperature cycle (e.g., daily cycle)
    
    # Sinusoidal variation to model day/night cycle
    temp_variation = amplitude * math.sin((2 * math.pi * time_step) / period)
    
    # Add some randomness to simulate real-world variation
    noise = random.uniform(-2, 2)
    
    return base_temp + temp_variation + noise

def holiday_model(time_step: int):
    return time_step % 4

# Negotiation Agent: Facilitates peer-to-peer energy trading
class House(Agent):
    class HouseStatus(CyclicBehaviour):
        async def on_start(self):
            self.idx = 0
            project_dir = os.path.dirname(os.path.dirname(__file__))
            data_path = os.path.join(project_dir,"models", "energy_test_set.npz")
            data = np.load(data_path)
            self.X_test = data["X_test"]
            self.Y_test = data["y_test"]

        async def run(self):
            await asyncio.sleep(5)
            print("[House] Sending current consumption and production data...")
            msg = await self.receive(timeout=5)

            test_sample = self.X_test[self.idx].reshape(1, self.X_test.shape[1], 1)
            actual_values = self.Y_test[self.idx]
            
            current_production = actual_values[0]
            current_demand = actual_values[1]

            temperature = temperature_model(self.idx)
            holiday = holiday_model(self.idx)
            power_per_device = current_demand/5

            self.idx = (self.idx + 1) % len(self.X_test)

            response = Message(to="facilitating@localhost")

            response.body = json.dumps({
                    "current_demand": current_demand,
                    "current_production": current_production,
                    "temperature" : temperature,
                    "holiday" : holiday,
                    "test_sample": test_sample.tolist(),  # Convert NumPy array to a Python list
                    "appliances": [
                        {"item": "Blender", 
                         "duration":random.randint(0, 200), 
                         "power_consumption":power_per_device},
                        {"item": "Game System", 
                         "duration":random.randint(0, 200), 
                         "power_consumption":power_per_device},
                        {"item": "TV", 
                         "duration":random.randint(0, 200), 
                         "power_consumption":power_per_device},
                        {"item": "Heater", 
                         "duration":random.randint(0, 200), 
                         "power_consumption":power_per_device},
                        {"item": "Washing Machine", 
                         "duration":random.randint(0, 200), 
                         "power_consumption":power_per_device}
                    ]
                })
            await self.send(response)
            print(f"[House] Sent current data to FacilitatingAgent: {response.body}")

    async def setup(self):
        print("[House] Started")
        self.add_behaviour(self.HouseStatus())
        self.web.start(hostname="localhost", port="9091")
