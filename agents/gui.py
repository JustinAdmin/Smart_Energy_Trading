from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import random
import asyncio

class GUIAgent(Agent):
    def __init__(self, jid, password):
        super().__init__(jid, password)
        self.energy_production = 0
        self.energy_consumption = 0
        self.energy_trade_strategy = "None"
        self.recommended_appliance_behaviours = []

    class guiBehaviour(CyclicBehaviour):
        async def run(self):
            # Simulate some work being done
            await asyncio.sleep(1)

    async def controller(self, request):
        """Handle web requests and return the updated number."""
        print("self.current_number")
        return {
            "energy_production": self.energy_production,
            "energy_consumption": self.energy_consumption,
            "energy_trade_strategy": self.energy_trade_strategy,
            "recommended_appliance_behaviours": self.recommended_appliance_behaviours
            }


    async def setup(self):
        print("[GUI] Started")
        self.add_behaviour(self.guiBehaviour())  # Start the cyclic behavior
        self.web.add_get("/home", self.controller, "/web/index.html")
        self.web.start(port=9099)
