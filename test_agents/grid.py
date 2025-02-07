from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import time

# Negotiation Agent: Facilitates peer-to-peer energy trading
class Grid(Agent):
    class GridBehavior(CyclicBehaviour):
        async def run(self):
            print("[Grid] Doing grid things...")
    
    async def setup(self):
        print("[House] Started")
        self.add_behaviour(self.GridBehavior())
        self.web.start(hostname="127.0.0.1", port="10010")