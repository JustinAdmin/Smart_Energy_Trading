from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import asyncio
import os
import joblib
import lightgbm as lgb

# Behavioral Segmentation Agent: Prioritizes appliance usage
class BehavioralSegmentationAgent(Agent):
    class SegmentationBehaviour(CyclicBehaviour):
        async def on_start(self):
            project_dir = os.path.dirname(os.path.dirname(__file__))
            model_filename = os.path.join(project_dir, "models", "lightgbm_ranker_model.pkl")
            self.model = joblib.load(model_filename)

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
                        
                        dataset = [
                            [
                                appliance["power_consumption"], 
                                data["temperature"], 
                                appliance["duration"], 
                                data["holiday"]
                            ] 
                            for appliance in data["appliances"]
                        ]
                        
                        priorities = self.model.predict(dataset)
                        for i, _ in enumerate(data["appliances"]):
                            data["appliances"][i]["priority"] = priorities[i]

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