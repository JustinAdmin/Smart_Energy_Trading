from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json

# Negotiation Agent: Facilitates peer-to-peer energy trading
class NegotiationAgent(Agent):
    class TradingBehaviour(CyclicBehaviour):
        async def run(self):
            print("[NegotiationAgent] Waiting for surplus energy data...")
            msg = await self.receive(timeout=5)
            if msg:
                try:
                    data = json.loads(msg.body).get("house")
                    print(f"[NegotiationAgent] Received data: {data}")
                    surplus_energy = data.get("current_production") - data.get("current_demand")
                    if surplus_energy > 0:
                        trade_amount = min(surplus_energy, 2.0)  # Simple trade rule
                        response = Message(to="facilitating@localhost")
                        response.body = json.dumps({
                            "traded_energy": trade_amount,
                            "energy_trade_strategy": "Bullish"
                            })
                        await self.send(response)
                        print(f"[NegotiationAgent] Sent trade decision to FacilitatingAgent: {response.body}")
                except json.JSONDecodeError:
                    print(f"[NegotiationAgent] Invalid message format: {msg.body}")
    
    async def setup(self):
        print("[NegotiationAgent] Started")
        self.add_behaviour(self.TradingBehaviour())
        self.web.start(hostname="localhost", port="9095")