from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
from datetime import datetime

# Function to determine the current energy rate based on timestamp
def get_energy_rate(timestamp):
    # Convert timestamp to datetime object
    current_time = datetime.fromtimestamp(timestamp)

    # Ultra-low rate: 11 PM to 7 AM
    if current_time.hour >= 23 or current_time.hour < 7:
        return 0.028  # 2.8¢ per kWh

    # Weekend off-peak: 7 AM to 11 PM on weekends
    elif current_time.weekday() in [5, 6]:  # Saturday or Sunday
        if 7 <= current_time.hour < 23:
            return 0.076  # 7.6¢ per kWh
        else:
            return 0.028  # 2.8¢ per kWh (Ultra-low during off-peak hours)

    # Weekday mid-peak: 7 AM to 4 PM, 9 PM to 11 PM
    elif current_time.weekday() in [0, 1, 2, 3, 4]:  # Monday to Friday
        if 7 <= current_time.hour < 16 or 21 <= current_time.hour < 23:
            return 0.122  # 12.2¢ per kWh (Mid-peak)
        elif 16 <= current_time.hour < 21:
            return 0.284  # 28.4¢ per kWh (On-peak)
    
    return 0.028  # Default to ultra-low rate

# Demand Response Agent: Manages energy curtailment based on grid demand
class DemandResponseAgent(Agent):
    class DRBehaviour(CyclicBehaviour):
        async def run(self):
            print("[DemandResponseAgent] Waiting for grid data...")
            msg = await self.receive(timeout=5)
            if msg:
                try:
                    # Get grid data and timestamp
                    data = json.loads(msg.body).get("grid")
                    timestamp = data.get("timestamp")  # Expected to be in UNIX timestamp format
                    
                    # Get the current energy rate based on the timestamp
                    energy_rate = get_energy_rate(timestamp)
                    print(f"[DemandResponseAgent] Current energy rate: {energy_rate} CAD per kWh")

                    print(f"[DemandResponseAgent] Received grid data: {data}")
                    if data.get("grid_demand") > 50:  # High grid demand condition
                        curtailment = data["household_power"] * 0.2
                    else:
                        curtailment = 0
                    
                    # Prepare the response with curtailment and energy rate
                    response = Message(to="facilitating@localhost")
                    response.body = json.dumps({
                        "curtailment": curtailment,
                        "recommended_appliance_behaviour": [
                            "Shut Off Blender", "Don't use Washing Machine", "Keep heater off between 4:00pm and 8:00pm"
                        ],
                        "energy_rate": energy_rate  # Send the determined energy rate along with the curtailment data
                    })
                    
                    await self.send(response)
                    print(f"[DemandResponseAgent] Sent curtailment and energy rate to FacilitatingAgent: {response.body}")

                except json.JSONDecodeError:
                    print(f"[DemandResponseAgent] Invalid message format: {msg.body}")
    
    async def setup(self):
        print("[DemandResponseAgent] Started")
        self.add_behaviour(self.DRBehaviour())
        self.web.start(hostname="localhost", port="9094")
