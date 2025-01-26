# Before you run this program ensure that you have SPADE installed with "pip install spade".
# In a separate terminal run the command "spade run" in the project folder to start the SPADE server.

import random
import asyncio

# These are the libraries that you will generally need to import for your agent
# (this does not count any AI or data processing libraries you use)
import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

# Here is an example agent, it extends the "Agent" class we imported from SPADE.
# **Note: This agent is NOT run when you run the example script.
class ExampleAgent(Agent):
    # Most agents will need to await signals from other agents, for this we will use
    # the CyclicBehaviour because it will handle loop behaviour and asynchronous messages.
    class AwaitingBehaviour(CyclicBehaviour):
        # We set up an async run function which will be run periodically in the main
        async def run(self):
            # Wait for message
            msg = await self.receive(timeout=5) # Check for messages in 5 second interval
            # If we receive a message...
            if msg:
                # Create a try catch block to check for invalid JSON messages
                try:
                    # Unpack the information in the message (stored in JSON format)
                    data = json.loads(msg.body)
                    # Data is now a dictionary with your desired variable names as keys with their corresponding values
                    example_value = data["example_value"]
                    # Now you can do logic (i.e. run your model) on the inputs
                    model_result = example_value/2
                    # Create a Message object to store your response
                    response = Message(to="facilitating@localhost")
                    # Store the response in a json object
                    response.body = json.dumps({
                        "key":"value",
                        "key2":"value",
                        "model_result":model_result
                    })

                    # Send the message
                    await self.send(response)
                # If we encounter an error we can specify which agent caught the error, and the message in question
                except json.JSONDecodeError:
                    print("[ExampleAgent] Invalid message format: {msg.body}")




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