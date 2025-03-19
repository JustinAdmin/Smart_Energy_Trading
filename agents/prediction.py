from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import time

# Prediction Agent: Forecasts energy demand and production
class PredictionAgent(Agent):
    class PredictBehaviour(CyclicBehaviour):
        async def run(self):
            print("[PredictionAgent] Waiting for input data...")
            msg = await self.receive(timeout=30)
            if msg:
                try:
                    data = json.loads(msg.body).get("house")
                    if data is None:
                        print("[PredictionAgent] No data received")
                    else:
                        print(f"[PredictionAgent] Received data: {data}")
                        predicted_demand = data['current_demand'] * 1.05  # Simple prediction logic
                        predicted_production = data['current_production'] * 0.95
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