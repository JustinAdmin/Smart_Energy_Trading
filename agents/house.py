from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import os
import asyncio
import numpy as np

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

            self.idx = (self.idx + 1) % len(self.X_test)

            response = Message(to="facilitating@localhost")

            response.body = json.dumps({
                    "current_demand": current_demand,
                    "current_production": current_production,
                    "test_sample": test_sample.tolist(),  # Convert NumPy array to a Python list
                    "appliances": [
                        {"item": "Blender", "priority": 1},
                        {"item": "Game System", "priority": 1},
                        {"item": "TV", "priority": 1},
                        {"item": "Heater", "priority": 4},
                        {"item": "Washing Machine", "priority": 3}
                    ]
                })
            await self.send(response)
            print(f"[House] Sent current data to FacilitatingAgent: {response.body}")

    async def setup(self):
        print("[House] Started")
        self.add_behaviour(self.HouseStatus())
        self.web.start(hostname="localhost", port="9091")
