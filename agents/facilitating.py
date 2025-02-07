from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json

class FacilitatingAgent(Agent):
    class MultiAgentHandler(CyclicBehaviour):
        def __init__(self):
            super().__init__()
            self.dependencies = {
                "prediction": [],
                "demandResponse": ["behavioralSegmentation", "prediction"],
                "negotiation": ["prediction"],
                "behavioralSegmentation": ["demandResponse", "prediction"]  # No dependencies
            }
            self.resolved = {agent: {"Status":False, "Msg":None} for agent in self.dependencies}
        async def run(self):
            # Wait for messages from any agent
            msg = await self.receive(timeout=5)  # Timeout in seconds
            if msg:
                sender = str(msg.sender)  # Sender's JID
                print(f"[FacilitatingAgent] Received message from {sender}: {msg.body}")

                # Example: Handle based on sender
                if sender == "prediction@localhost":
                    print("[FacilitatingAgent] Prediction received.")
                    self.resolved["prediction"]["Status"] = True
                    self.resolved["prediction"]["Msg"] = msg.body

                elif sender == "demandResponse@localhost":
                    print("[FacilitatingAgent] Demand response received.")
                    self.resolved["demandResponse"]["Status"] = True
                    self.resolved["demandResponse"]["Msg"] = msg.body

                elif sender == "negotiation@localhost":
                    print("[FacilitatingAgent] Negotiation message received.")
                    self.resolved["negotiation"]["Status"] = True
                    self.resolved["negotiation"]["Msg"] = msg.body

                elif sender == "behavioralSegmentation@localhost":
                    print("[FacilitatingAgent] Behavioral segmentation message received.")
                    self.resolved["behavioralSegmentation"]["Status"] = True
                    self.resolved["behavioralSegmentation"]["Msg"] = msg.body

                else:
                    print(f"[FacilitatingAgent] Message received from unknown agent: {sender}")
            else:
                print("[FacilitatingAgent] No message received.")

            print("[FacilitatingAgent] Handling received messages...")
            for agent in self.dependencies:
                print(f"[FacilitatingAgent] Checking {agent} dependencies...")

                # Check for unresolved dependencies
                unresolved_dependencies = []
                for dependency in self.dependencies[agent]:
                    if self.resolved[dependency]['Status'] == False:
                        unresolved_dependencies.append(dependency)

                #  If no dependencies are unresolved
                if len(unresolved_dependencies) == 0:
                    print(f"[FacilitatingAgent] Dependencies resolved for {agent}, sending message...")

                    # Set message for agent
                    agent_address = f"{agent}@localhost"

                    dict = {}
                    for dependency in self.dependencies[agent]:
                        dict[dependency] = self.resolved[dependency]["Msg"]
                    if agent == "prediction":
                        dict["current_demand"] = 100
                        dict["current_production"] = 100

                    try:
                        json_dump = json.dumps(dict)
                        response = Message(to=agent_address, body=json_dump)
                        await self.send(response)
                        print(f"[FacilitatingAgent] Sent message to {agent}")
                    except json.JSONDecodeError:
                        print(f"[PredictionAgent] Invalid message format: {msg.body}")

                else:
                    print(f"[FacilitatingAgent] Awaiting dependencies for agent {agent}:")
                    for dependency in unresolved_dependencies:
                        print(dependency)


    async def setup(self):
        print("[FacilitatingAgent] Started")
        handler = self.MultiAgentHandler()
        self.add_behaviour(handler)
