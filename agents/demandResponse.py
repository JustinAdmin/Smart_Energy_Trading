from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json

# Demand Response Agent: Manages energy curtailment based on grid demand
class DemandResponseAgent(Agent):
    class DRBehaviour(CyclicBehaviour):
        async def run(self):
            print("[DemandResponseAgent] Waiting for grid data...")
            msg = await self.receive(timeout=5)
            if msg:
                try:
                    data = json.loads(msg.body).get("grid")
                    print(f"[DemandResponseAgent] Received data: {data}")
                    if data.get("grid_demand") > 50:
                        curtailment = data["household_power"] * 0.2
                    else:
                        curtailment = 0
                    response = Message(to="facilitating@localhost")
                    response.body = json.dumps({
                        "curtailment": curtailment,
                        "recommended_appliance_behaviour": ["Shut Off Blender", "Don't use Washing Machine", "Keep heater off between 4:00pm and 8:00pm"]
                        })
                    await self.send(response)
                    print(f"[DemandResponseAgent] Sent curtailment action to FacilitatingAgent: {response.body}")
                except json.JSONDecodeError:
                    print(f"[DemandResponseAgent] Invalid message format: {msg.body}")
    
    async def setup(self):
        print("[DemandResponseAgent] Started")
        self.add_behaviour(self.DRBehaviour())
        self.web.start(hostname="localhost", port="9094")