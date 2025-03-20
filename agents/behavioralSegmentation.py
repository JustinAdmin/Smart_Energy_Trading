from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import asyncio

# Behavioral Segmentation Agent: Prioritizes appliance usage
class BehavioralSegmentationAgent(Agent):
    class SegmentationBehaviour(CyclicBehaviour):
        async def run(self):
            await asyncio.sleep(5)
            print("[BehavioralSegmentationAgent] Waiting for appliance data...")
            msg = await self.receive(timeout=30)
            if msg:
                try:
                    data = json.loads(msg.body).get("house")
                    if data is None:
                        print("[BehavioralSegmentationAgent] No data received")
                    else:
                        print(f"[BehavioralSegmentationAgent] Received data: {data}")
                        prioritized_appliances = sorted(data["appliances"], key=lambda x: x["priority"], reverse=True)
                        response = Message(to="facilitating@localhost")
                        response.body = json.dumps({"prioritized_appliances": prioritized_appliances})
                        await self.send(response)
                        print(f"[BehavioralSegmentationAgent] Sent appliance priority list to FacilitatingAgent: {response.body}")
                except Exception as e:
                    print(f"[BehavioralSegmentationAgent] Error: {e}")
                    print(f"[BehavioralSegmentationAgent] {msg}")
    
    async def setup(self):
        print("[BehavioralSegmentationAgent] Started")
        self.add_behaviour(self.SegmentationBehaviour())
        self.web.start(hostname="localhost", port="9093")