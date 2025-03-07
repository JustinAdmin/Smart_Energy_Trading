from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json

# Behavioral Segmentation Agent: Prioritizes appliance usage
class BehavioralSegmentationAgent(Agent):
    class SegmentationBehaviour(CyclicBehaviour):
        async def run(self):
            print("[BehavioralSegmentationAgent] Waiting for appliance data...")
            msg = await self.receive(timeout=5)
            if msg:
                try:
                    data = json.loads(msg.body).get("house")
                    print(f"[BehavioralSegmentationAgent] Received data: {data}")
                    prioritized_appliances = sorted(data["appliances"], key=lambda x: x["priority"], reverse=True)
                    response = Message(to="facilitating@localhost")
                    response.body = json.dumps({"prioritized_appliances": prioritized_appliances})
                    await self.send(response)
                    print(f"[BehavioralSegmentationAgent] Sent appliance priority list to FacilitatingAgent: {response.body}")
                except json.JSONDecodeError:
                    print(f"[BehavioralSegmentationAgent] Invalid message format: {msg.body}")
    
    async def setup(self):
        print("[BehavioralSegmentationAgent] Started")
        self.add_behaviour(self.SegmentationBehaviour())
        self.web.start(hostname="localhost", port="9093")