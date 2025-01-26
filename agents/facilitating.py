from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

class FacilitatingAgent(Agent):
    def __init__(self, jid, password):
        super().__init__(jid, password)
        self.dependencies = {
            "AgentA": ["AgentB", "AgentC"],
            "AgentB": ["AgentC"],
            "AgentC": ["AgentD"],
            "AgentD": []  # No dependencies
        }
        self.resolved = {agent: False for agent in self.dependencies}

    class MultiAgentHandler(CyclicBehaviour):
        async def run(self):
            # Wait for messages from any agent
            msg = await self.receive(timeout=5)  # Timeout in seconds
            if msg:
                sender = str(msg.sender)  # Sender's JID
                print(f"Received message from {sender}: {msg.body}")

                # Example: Handle based on sender
                if sender == "agentA@localhost":
                    print("Processing task from Agent A...")
                    response = Message(to="agentB@localhost")
                    response.body = "Agent A sent info. Forwarding to Agent B."
                    await self.send(response)

                elif sender == "agentB@localhost":
                    print("Processing task from Agent B...")
                    response = Message(to="agentC@localhost")
                    response.body = "Agent B sent info. Forwarding to Agent C."
                    await self.send(response)

                elif sender == "agentC@localhost":
                    print("Received message from Agent C. Completing process...")
                    response = Message(to="agentA@localhost")
                    response.body = "Agent C's task complete. Notifying Agent A."
                    await self.send(response)

                else:
                    print(f"Message received from unknown agent: {sender}")
            else:
                print("No messages received. Waiting...")

    async def setup(self):
        print("Facilitating Agent starting...")
        handler = self.MultiAgentHandler()
        self.add_behaviour(handler)
