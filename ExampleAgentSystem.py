# Before you run this program ensure that you have SPADE installed with "pip install spade".
# In a separate terminal run the command "spade run" in the project folder to start the SPADE server.

import time
import asyncio

# These are the libraries that you will generally need to import for your agent
# (this does not count any AI or data processing libraries you use)
import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

# Here is an example agent, it extends the "Agent" class we imported from SPADE.
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
                    example_value = data["example_data"]
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
                    # Set the sender to your agents ID
                    # Send the message
                    await self.send(response)
                    print(f"[ExampleAgent] Message {model_result} sent!")
                # If we encounter an error we can specify which agent caught the error, and the message in question
                except json.JSONDecodeError:
                    print(f"[ExampleAgent] Invalid message format: {msg.body}")

    async def setup(self):
        e = self.AwaitingBehaviour()
        self.add_behaviour(e)




# This is a demo agent that simulates a facilitating agent
class Facilitating(Agent):
    class FacilitatingBehaviour(CyclicBehaviour):
        async def run(self):
            msg = Message(to="example@localhost")
            data = {
                "example_data":100
            }
            msg.body = json.dumps(data)
            await self.send(msg)
            time.sleep(5)

    async def setup(self):
        f = self.FacilitatingBehaviour()
        self.add_behaviour(f)




# This is what our main file will look like (except with all our agents)
async def main():
    # Create agents
    example_agent = ExampleAgent("example@localhost", "password")
    facilitating_agent = Facilitating("facilitating@localhost", "password")

    # Start agents
    await example_agent.start()
    await facilitating_agent.start()


# Run the multi-agent system
if __name__ == "__main__":
    asyncio.run(main())