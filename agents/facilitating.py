from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import time

class FacilitatingAgent(Agent):
    class MultiAgentHandler(CyclicBehaviour):
        def __init__(self):
            super().__init__()
            self.dependencies = {
                "prediction": ["house"],
                "demandResponse": ["behavioralSegmentation", "prediction"],
                "negotiation": ["prediction"],
                "behavioralSegmentation": ["demandResponse", "prediction"],
                "grid" : ["negotiation"],
                "house" : []
            }
            self.resolved = {agent: {"Status":False, "Msg":None} for agent in self.dependencies}
            self.startup = True

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
                    self.resolved["prediction"]["Msg"] = json.loads(msg.body)

                elif sender == "demandResponse@localhost":
                    print("[FacilitatingAgent] Demand response received.")
                    self.resolved["demandResponse"]["Status"] = True
                    self.resolved["demandResponse"]["Msg"] = json.loads(msg.body)

                elif sender == "negotiation@localhost":
                    print("[FacilitatingAgent] Negotiation message received.")
                    self.resolved["negotiation"]["Status"] = True
                    self.resolved["negotiation"]["Msg"] = json.loads(msg.body)

                elif sender == "behavioralSegmentation@localhost":
                    print("[FacilitatingAgent] Behavioral segmentation message received.")
                    self.resolved["behavioralSegmentation"]["Status"] = True
                    self.resolved["behavioralSegmentation"]["Msg"] = json.loads(msg.body)

                elif sender == "house@localhost":
                    print("[FacilitatingAgent] House status received.")
                    self.resolved["house"]["Status"] = True
                    self.resolved["house"]["Msg"] = json.loads(msg.body)

                elif sender == "grid@localhost":
                    print("[FacilitatingAgent] Grid status received.")
                    self.resolved["grid"]["Status"] = True
                    self.resolved["grid"]["Msg"] = json.loads(msg.body)

                else:
                    print(f"[FacilitatingAgent] Message received from unknown agent: {sender}")
            else:
                print("[FacilitatingAgent] No message received.")

            time.sleep(1)
            print("[FacilitatingAgent] Handling received messages...")
            for agent in self.dependencies:
                time.sleep(1)
                if agent!= "house":
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

                        # Get all the messages from the resolved agents
                        dict = {}
                        for dependency in self.dependencies[agent]:
                            dict[dependency] = self.resolved[dependency]["Msg"]

                        # Try sending message
                        try:
                            json_dump = json.dumps(dict)
                            response = Message(to=agent_address, body=json_dump)
                            await self.send(response)
                            print(f"[FacilitatingAgent] Sent message to {agent}")

                            # Set status back to false since agent is thinking of a new answer
                            self.resolved[agent]["Status"] = False
                        except json.JSONDecodeError:
                            print(f"[PredictionAgent] Invalid message format: {msg.body}")

                    # Print dependencies that have not yet been fulfilled (this way we know if a specific agent is blocking the system)
                    else:
                        print(f"[FacilitatingAgent] Awaiting dependencies for agent {agent}:")
                        for dependency in unresolved_dependencies:
                            print(dependency)


    async def setup(self):
        print("[FacilitatingAgent] Started")
        handler = self.MultiAgentHandler()
        self.add_behaviour(handler)
        self.web.start(hostname="127.0.0.1", port="10000")