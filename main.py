import subprocess
import time
import asyncio
import os
from agents.behavioralSegmentation import BehavioralSegmentationAgent
from agents.demandResponse import DemandResponseAgent
from agents.facilitating import FacilitatingAgent
from agents.negotiation import NegotiationAgent
from agents.prediction import PredictionAgent
from agents.gui import GUIAgent
from agents.grid import Grid
from agents.house import House

def start_spade():
    print("🟡 Starting SPADE server in a new PowerShell window...")
    spade_process = subprocess.Popen(["powershell", "-Command", "Start-Process", "powershell", "-ArgumentList 'spade run'"])
    time.sleep(1)
    print("✅ SPADE server started in a separate window!")
    return spade_process

def start_streamlit():
    print("🟡 Starting Streamlit UI in a new PowerShell window...")
    streamlit_process = subprocess.Popen(["powershell", "-Command", "Start-Process", "powershell", "-ArgumentList 'streamlit run streamlit_gui.py'"])
    time.sleep(1)
    print("✅ Streamlit UI started in a separate window!")
    return streamlit_process

def start_ganache():
    print("🟡 Starting Ganache CLI in a new PowerShell window...")
    ganache_process = subprocess.Popen(["powershell", "-Command", "Start-Process", "powershell", "-ArgumentList 'ganache-cli --networkId 4447'"])
    time.sleep(2)
    print("✅ Ganache CLI started in a separate window!")
    return ganache_process

def deploy_smart_contract():
    print("🟡 Deploying the smart contract...")
    print(f"Current working directory: {os.getcwd()}")
    
    # Update the Popen command to use the 'development' network defined in truffle-config.js
    deployment_process = subprocess.Popen(["powershell", "-Command",
                                           "Start-Process", "powershell",
                                           "-ArgumentList 'truffle migrate --network development'"],
                                           cwd=os.getcwd())
    time.sleep(2)  # Allow time for the process to start
    print("✅ Smart contract deployed!")
    return deployment_process

async def main():
    print("🟡 Initializing agents...")

    gui = GUIAgent("gui@localhost", "password")
    house = House("house@localhost", "password")
    grid = Grid("grid@localhost", "password")
    behavioral_segmentation_agent = BehavioralSegmentationAgent("behavioralsegmentation@localhost", "password")
    demand_response_agent = DemandResponseAgent("demandresponse@localhost", "password")
    negotiation_agent = NegotiationAgent("negotiation@localhost", "password")
    prediction_agent = PredictionAgent("prediction@localhost", "password")
    facilitating_agent = FacilitatingAgent("facilitating@localhost", "password")

    await gui.start()
    await house.start()
    await grid.start()
    await behavioral_segmentation_agent.start()
    await demand_response_agent.start()
    await negotiation_agent.start()
    await prediction_agent.start()
    await facilitating_agent.start()
    print("✅ All agents started!")

if __name__ == "__main__":
    print("🚀 Launching the Multi-Agent System...")

    spade_process = start_spade()     # Start SPADE server
    streamlit_process = start_streamlit()  # Start Streamlit UI
    ganache_process = start_ganache()  # Start Ganache CLI
    deployment_process = deploy_smart_contract()  # Deploy the smart contract

    print("🟡 Running Multi-Agent System...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Shutting down processes...")
        spade_process.kill()
        streamlit_process.kill()
        ganache_process.kill()
        deployment_process.kill()
        print("✅ Cleanup complete. Exiting.")
