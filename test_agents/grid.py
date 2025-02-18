from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import numpy as np
import time

# Negotiation Agent: Facilitates peer-to-peer energy trading
class Grid(Agent):
    class GridBehavior(CyclicBehaviour):
        async def on_start(self):
            self.grid_demand = 0

        async def run(self):
            msg = await self.receive(timeout=5)
            print("[Grid] Sending Grid Data")
            response = Message(to="facilitating@localhost")
            grid_demand = np.sin(self.grid_demand) * 20
            self.grid_demand += 0.1
            response.body = json.dumps({
                "grid_demand":grid_demand,
                "household_power":100
                })
            await self.send(response)
            print("[Grid] Sent grid demand data to FacilitatingAgent")
    async def setup(self):
        print("[House] Started")
        self.add_behaviour(self.GridBehavior())
        self.web.start(hostname="localhost", port="9092")