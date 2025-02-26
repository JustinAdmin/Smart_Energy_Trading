from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import random

class GUIAgent(Agent):
    class guiBehaviour(CyclicBehaviour):
        async def run(self):
            print("[GUI] Waiting for messages...")
            msg = await self.receive(timeout=5)
            if msg:
                try:
                    data = json.loads(msg.body)
                    print(f"[GUI] Received data: {data}")
                    pass
                    response = Message(to="facilitating@localhost")
                    response.body = json.dumps({"key": "value"})
                    await self.send(response)
                    print(f"[GUI] Sent requests to FacilitatingAgent: {response.body}")
                except json.JSONDecodeError:
                    print(f"[GUI] Invalid message format: {msg.body}")

    async def controller(self, request):
        return {"number": 42}
    
    async def setup(self):
        print("[GUI] Started")
        self.add_behaviour(self.guiBehaviour())
        self.web.add_get("/home", self.controller, "/web/index.html")
        self.web.start(port=9099)