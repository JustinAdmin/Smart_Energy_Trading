from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import numpy as np
import asyncio
import os

# Negotiation Agent: Facilitates peer-to-peer energy trading
class Grid(Agent):
    class GridBehavior(CyclicBehaviour):
        async def on_start(self):
            self.grid_demand = 0
            self.idx = 24
            project_dir = os.path.dirname(os.path.dirname(__file__))
            data_path_demand = os.path.join(project_dir,"models", "energy_X_test_demand_set.npz")
            data_path_supply = os.path.join(project_dir,"models", "energy_X_test_supply_set.npz")
            data_demand = np.load(data_path_demand)
            data_supply = np.load(data_path_supply)
            self.X_test_supply = data_supply["X_test"]
            self.Y_test_supply = data_supply["y_test"]
            self.X_test_demand = data_demand["X_test"]
            self.Y_test_demand = data_demand["y_test"]    

        async def run(self):
            await asyncio.sleep(5)
            print("[Grid] Sending Grid Demand and Supply Data")
            msg = await self.receive(timeout=5)
            
            print(f"Before Reshaping - X_test_supply: {self.X_test_supply.shape}, X_test_demand: {self.X_test_demand.shape}")
            
            test_sample_supply = self.X_test_supply[self.idx-24:self.idx]
            test_sample_demand = self.X_test_demand[self.idx-24:self.idx]
            
            actual_supply = self.Y_test_supply[self.idx]
            actual_demand = self.Y_test_demand[self.idx]
            
            # print(f"After Reshaping - test_sample_supply: {test_sample_supply.shape}, test_sample_demand: {test_sample_demand.shape}")
            
            # Ensure index stays between 24 and the length of the array
            self.idx = (self.idx + 1) % len(self.X_test_supply)
            if self.idx < 24:
                self.idx = 24
            
            response = Message(to="facilitating@localhost")
            response.body = json.dumps({
                "grid_demand": actual_demand.tolist(),
                "grid_supply": actual_supply.tolist(),
                "test_sample_supply": test_sample_supply.tolist(),
                "test_sample_demand": test_sample_demand.tolist()
            })

   
        # async def run(self):
        #     await asyncio.sleep(5)
        #     msg = await self.receive(timeout=5)
        #     print("[Grid] Sending Grid Data")
        #     response = Message(to="facilitating@localhost")
        #     grid_demand = np.sin(self.grid_demand) * 20
        #     self.grid_demand += 0.1
        #     response.body = json.dumps({
        #         "grid_demand":grid_demand,
        #         "household_power":100
        #         })
            
            await self.send(response)
            print("[Grid] Sent grid demand data to FacilitatingAgent")

    async def setup(self):
        print("[House] Started")
        self.add_behaviour(self.GridBehavior())
        self.web.start(hostname="localhost", port="9092")