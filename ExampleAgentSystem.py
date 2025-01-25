# Before you run this program ensure that you have SPADE installed with "pip install spade". 
# In a seperate terminal run the commmand "spade run" to start the SPADE server.

import asyncio
import random
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

class InformationGatheringAgent(Agent):
    class GatherInformationBehaviour(CyclicBehaviour):
        async def run(self):
            # Simulated API call (dummy implementation)
            information = self.simulate_api_search()
            
            # Send information to mediator
            msg = Message(to="mediator@localhost")
            msg.set_metadata("performative", "inform")
            msg.body = information
            await self.send(msg)
            
            # Wait before next search
            await asyncio.sleep(10)
        
        def simulate_api_search(self):
            # Simulate fetching information from a dummy API
            topics = ['technology', 'science', 'politics', 'sports']
            return f"Latest news in {random.choice(topics)}: {random.randint(1000, 9999)}"

class MediatorAgent(Agent):
    class MediationBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                # Forward received information to action agent
                forward_msg = Message(to="action@localhost")
                forward_msg.set_metadata("performative", "inform")
                forward_msg.body = msg.body
                await self.send(forward_msg)

class ActionAgent(Agent):
    class ActionBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                # Perform action based on received information
                print(f"Action triggered: {msg.body}")

async def main():
    # Create agents
    information_agent = InformationGatheringAgent("information@localhost", "password")
    mediator_agent = MediatorAgent("mediator@localhost", "password")
    action_agent = ActionAgent("action@localhost", "password")

    # Start agents
    await information_agent.start()
    await mediator_agent.start()
    await action_agent.start()

    # Add behaviours
    information_agent.add_behaviour(information_agent.GatherInformationBehaviour())
    mediator_agent.add_behaviour(mediator_agent.MediationBehaviour())
    action_agent.add_behaviour(action_agent.ActionBehaviour())

# Run the multi-agent system
if __name__ == "__main__":
    asyncio.run(main())