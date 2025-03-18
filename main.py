import subprocess
import time
import asyncio
import requests
import os
from agents.behavioralSegmentation import BehavioralSegmentationAgent
from agents.demandResponse import DemandResponseAgent
from agents.facilitating import FacilitatingAgent
from agents.negotiation import NegotiationAgent
from agents.prediction import PredictionAgent
from agents.gui import GUIAgent
from test_agents.grid import Grid
from test_agents.house import House

GANACHE_PORT = 8545
GANACHE_DB_PATH = "./ganache-data"

def is_ganache_running():
    try:
        response = requests.post(f"http://localhost:{GANACHE_PORT}", json={})
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def start_ganache():
    if is_ganache_running():
        print(f"✅ Ganache is already running on port {GANACHE_PORT}")
        return None

    print("🟡 Starting Ganache...")
    if not os.path.exists(GANACHE_DB_PATH):
        os.makedirs(GANACHE_DB_PATH)

    ganache_process = subprocess.Popen([
        "npx", "ganache",
        "--port", str(GANACHE_PORT),
        "--db", GANACHE_DB_PATH,
        "--chainId", "1337",
        "--server", "localhost",
        "--defaultBalanceEther", "1000"
    ])

    # Wait until Ganache is ready
    while not is_ganache_running():
        time.sleep(1)

    print(f"✅ Ganache started on port {GANACHE_PORT}")
    return ganache_process

def deploy_contract():
    print("🟡 Deploying contract...")
    subprocess.run(["npx", "hardhat", "run", "scripts/deploy.js", "--network", "localhost"])
    print("✅ Contract deployed successfully.")
    time.sleep(2)

def start_spade():
    print("🟡 Starting SPADE server in a new PowerShell window...")
    spade_process = subprocess.Popen(["powershell", "-Command", "Start-Process", "powershell", "-ArgumentList 'spade run'"])
    time.sleep(5)
    print("✅ SPADE server started in a separate window!")
    return spade_process

def start_streamlit():
    print("🟡 Starting Streamlit UI in a new PowerShell window...")
    streamlit_process = subprocess.Popen(["powershell", "-Command", "Start-Process", "powershell", "-ArgumentList 'streamlit run streamlit_gui.py'"])
    print("✅ Streamlit UI started in a separate window!")
    return streamlit_process

async def main():
    print("🟡 Initializing agents...")
    gui = GUIAgent("gui@localhost", "password")
    house = House("house@localhost", "password")
    grid = Grid("grid@localhost", "password")
    behavioral_segmentation_agent = BehavioralSegmentationAgent("behavioralsegmentation@localhost", "password")
    demand_response_agent = DemandResponseAgent("demandResponse@localhost", "password")
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

    ganache_process = start_ganache()  # Start Ganache
    deploy_contract()                 # Deploy Contract

    spade_process = start_spade()     # Start SPADE server
    streamlit_process = start_streamlit()  # Start Streamlit UI

    print("🟡 Running Multi-Agent System...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Shutting down processes...")
        if ganache_process:
            ganache_process.terminate()
            ganache_process.wait()
        spade_process.terminate()
        streamlit_process.terminate()
        print("✅ Cleanup complete. Exiting.")
