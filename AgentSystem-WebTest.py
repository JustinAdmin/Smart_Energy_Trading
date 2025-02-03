import time
import asyncio
import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

# Prediction Agent: Forecasts energy demand and production
class PredictionAgent(Agent):
    class PredictBehaviour(CyclicBehaviour):
        async def run(self):
            print("[PredictionAgent] Waiting for input data...")
            msg = await self.receive(timeout=5)
            if msg:
                try:
                    data = json.loads(msg.body)
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
                except json.JSONDecodeError:
                    print(f"[PredictionAgent] Invalid message format: {msg.body}")
    
    async def setup(self):
        print("[PredictionAgent] Started")
        self.add_behaviour(self.PredictBehaviour())
        self.web.start(hostname="127.0.0.1", port="10001")

# Demand Response Agent: Manages energy curtailment based on grid demand
class DemandResponseAgent(Agent):
    class DRBehaviour(CyclicBehaviour):
        async def run(self):
            print("[DemandResponseAgent] Waiting for grid data...")
            msg = await self.receive(timeout=5)
            if msg:
                try:
                    data = json.loads(msg.body)
                    print(f"[DemandResponseAgent] Received data: {data}")
                    if data.get("grid_demand") > 50:
                        curtailment = data["household_power"] * 0.2
                    else:
                        curtailment = 0
                    response = Message(to="facilitating@localhost")
                    response.body = json.dumps({"curtailment": curtailment})
                    await self.send(response)
                    print(f"[DemandResponseAgent] Sent curtailment action to FacilitatingAgent: {response.body}")
                except json.JSONDecodeError:
                    print(f"[DemandResponseAgent] Invalid message format: {msg.body}")
    
    async def setup(self):
        print("[DemandResponseAgent] Started")
        self.add_behaviour(self.DRBehaviour())
        self.web.start(hostname="127.0.0.1", port="10002")

# Behavioral Segmentation Agent: Prioritizes appliance usage
class BehavioralSegmentationAgent(Agent):
    class SegmentationBehaviour(CyclicBehaviour):
        async def run(self):
            print("[BehavioralSegmentationAgent] Waiting for appliance data...")
            msg = await self.receive(timeout=5)
            if msg:
                try:
                    data = json.loads(msg.body)
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
        self.web.start(hostname="127.0.0.1", port="10003")

# Negotiation Agent: Facilitates peer-to-peer energy trading
class NegotiationAgent(Agent):
    class TradingBehaviour(CyclicBehaviour):
        async def run(self):
            print("[NegotiationAgent] Waiting for surplus energy data...")
            msg = await self.receive(timeout=5)
            if msg:
                try:
                    data = json.loads(msg.body)
                    print(f"[NegotiationAgent] Received data: {data}")
                    if data.get("surplus_energy") > 0:
                        trade_amount = min(data["surplus_energy"], 2.0)  # Simple trade rule
                        response = Message(to="facilitating@localhost")
                        response.body = json.dumps({"traded_energy": trade_amount})
                        await self.send(response)
                        print(f"[NegotiationAgent] Sent trade decision to FacilitatingAgent: {response.body}")
                except json.JSONDecodeError:
                    print(f"[NegotiationAgent] Invalid message format: {msg.body}")
    
    async def setup(self):
        print("[NegotiationAgent] Started")
        self.add_behaviour(self.TradingBehaviour())
        self.web.start(hostname="127.0.0.1", port="10004")

# Facilitating Agent: Coordinates communication between all agents
class FacilitatingAgent(Agent):
    class CoordinationBehaviour(CyclicBehaviour):
        async def run(self):
            user_input = input("Start simulation? (yes/no): ")
            if user_input.lower() != "yes":
                print("[FacilitatingAgent] Simulation aborted by user.")
                return
            
            print("[FacilitatingAgent] Starting simulation...")
            data = {
                "current_demand": 10,
                "current_production": 12,
                "grid_demand": 55,
                "household_power": 6,
                "appliances": [{"name": "Fridge", "priority": 3}, {"name": "Washer", "priority": 1}],
                "surplus_energy": 2.5
            }
            
            print("[FacilitatingAgent] Sending data to all agents...")
            for agent in ["prediction", "demand_response", "behavioral_segmentation", "negotiation"]:
                msg = Message(to=f"{agent}@localhost")
                msg.body = json.dumps(data)
                await self.send(msg)
                print(f"[FacilitatingAgent] Sent data to {agent}.")
            
            time.sleep(5)
            print("[FacilitatingAgent] Simulation cycle complete.")
    
    async def setup(self):
        print("[FacilitatingAgent] Started")
        self.add_behaviour(self.CoordinationBehaviour())
        self.web.start(hostname="127.0.0.1", port="10005")

# Main function to run the agents
async def main():
    print("[System] Initializing agents...")
    agents = [
        PredictionAgent("prediction@localhost", "password"),
        DemandResponseAgent("demand_response@localhost", "password"),
        BehavioralSegmentationAgent("behavioral_segmentation@localhost", "password"),
        NegotiationAgent("negotiation@localhost", "password"),
        FacilitatingAgent("facilitating@localhost", "password")
    ]
    
    for agent in agents:
        await agent.start()
    
    print("[System] All agents started. Running simulation...")
    await asyncio.sleep(30)
    
    print("[System] Stopping agents...")
    for agent in agents:
        await agent.stop()
    print("[System] Simulation ended.")

if __name__ == "__main__":
    asyncio.run(main())
