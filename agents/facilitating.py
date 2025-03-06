import json
from datetime import datetime
import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

# Define the FacilitatingAgent class as before
class FacilitatingAgent(Agent):
    class MultiAgentHandler(CyclicBehaviour):
        async def on_start(self):
            self.dependencies = {
                "gui": ["house", "negotiation", "demandResponse"],
                "prediction": ["house"],
                "demandResponse": ["grid", "behavioralsegmentation"],
                "negotiation": ["house", "prediction"],
                "behavioralsegmentation": ["prediction", "house"],
                "grid" : ["negotiation"],
                "house" : []
            }
            self.last_message = {agent: {"time": datetime.now(), "msg": None} for agent in self.dependencies}
            self.startup = True

        async def run(self):
            def time_from_now(message_timing):
                return (datetime.now() - message_timing["time"]).total_seconds()
            
            # Wait for messages from any agent
            msg = await self.receive(timeout=5)  # Timeout in seconds
            if msg:
                sender = str(msg.sender)  # Sender's JID
                print(f"[FacilitatingAgent] Received message from {sender}: {msg.body}")

                # Example: Handle based on sender
                if sender == "prediction@localhost" and time_from_now(self.last_message["prediction"]) > 3:
                    print("[FacilitatingAgent] Prediction received.")
                    self.last_message["prediction"]["time"] = datetime.now()
                    self.last_message["prediction"]["msg"] = json.loads(msg.body)

                elif sender == "demandResponse@localhost" and time_from_now(self.last_message["demandResponse"]) > 3:
                    print("[FacilitatingAgent] Demand response received.")
                    self.last_message["demandResponse"]["time"] = datetime.now()
                    self.last_message["demandResponse"]["msg"] = json.loads(msg.body)

                elif sender == "negotiation@localhost" and time_from_now(self.last_message["negotiation"]) > 3:
                    print("[FacilitatingAgent] Negotiation message received.")
                    self.last_message["negotiation"]["time"] = datetime.now()
                    self.last_message["negotiation"]["msg"] = json.loads(msg.body)

                elif sender == "behavioralsegmentation@localhost" and time_from_now(self.last_message["behavioralsegmentation"]) > 3:
                    print("[FacilitatingAgent] Behavioral segmentation message received.")
                    self.last_message["behavioralsegmentation"]["time"] = datetime.now()
                    self.last_message["behavioralsegmentation"]["msg"] = json.loads(msg.body)

                elif sender == "house@localhost" and time_from_now(self.last_message["house"]) > 3:
                    print("[FacilitatingAgent] House status received.")
                    self.last_message["house"]["time"] = datetime.now()
                    self.last_message["house"]["msg"] = json.loads(msg.body)

                elif sender == "grid@localhost" and time_from_now(self.last_message["grid"]) > 3:
                    print("[FacilitatingAgent] Grid status received.")
                    self.last_message["grid"]["time"] = datetime.now()
                    self.last_message["grid"]["msg"] = json.loads(msg.body)

                else:
                    print(f"[FacilitatingAgent] !!Message received from unknown agent: {sender}!!")

            else:
                print("[FacilitatingAgent] No message received.")

            # Update dependencies and send responses if needed
            for agent in self.dependencies:
                unresolved_dependencies = []
                for dependency in self.dependencies[agent]:
                    if time_from_now(self.last_message[dependency]) > 10:
                        unresolved_dependencies.append(dependency)

                if len(self.dependencies[agent]) != 0:
                    if len(unresolved_dependencies) == 0:
                        print(f"[FacilitatingAgent] Dependencies resolved for {agent}, sending message...")

                        agent_address = f"{agent}@localhost"
                        dict = {}
                        for dependency in self.dependencies[agent]:
                            dict[dependency] = self.last_message[dependency]["msg"]

                        try:
                            json_dump = json.dumps(dict)
                            response = Message(to=agent_address, body=json_dump)
                            await self.send(response)
                            print(f"[FacilitatingAgent] Sent message to {agent}")
                        except json.JSONDecodeError:
                            print(f"[FacilitatingAgent] Invalid message format: {msg.body}")
                    else:
                        print(f"[FacilitatingAgent] Awaiting dependencies for agent {agent}:")
                        for dependency in unresolved_dependencies:
                            print(dependency)
                else:
                    print(f"[FacilitatingAgent] {agent} has no dependencies.")

    async def setup(self):
        print("[FacilitatingAgent] Started")
        handler = self.MultiAgentHandler()
        self.add_behaviour(handler)

