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
    """Starts Ganache CLI in a separate PowerShell window."""
    print("🟡 Starting Ganache CLI...")
    try:
        # Add --hardfork shanghai
        ganache_args = "'ganache-cli --networkId 5777 --hardfork shanghai'"
        command_list = ["powershell", "-Command", "Start-Process", "powershell", "-ArgumentList", ganache_args]
        ganache_process = subprocess.Popen(command_list)
        print("   Waiting for Ganache to initialize (using Shanghai hardfork)...")
        time.sleep(5)
        print("✅ Ganache CLI should be running in a separate window.")
        return ganache_process
    except FileNotFoundError:
        print("❌ Error: 'powershell' or 'ganache-cli' command not found.")
        return None
    except Exception as e:
        print(f"❌ Error starting Ganache: {e}")
        return None

def deploy_smart_contract():
    """Deploys the smart contract using Truffle in a separate PowerShell window."""
    print("🟡 Deploying the smart contract...")
    project_root = os.path.dirname(os.path.dirname(__file__))
    blockchain_dir = os.path.join(project_root,"5014-Project", "blockchain")
    print(f"   Running deployment from project root: {project_root}")
    print(f"   Expecting 'blockchain' directory at: {blockchain_dir}")

    if not os.path.isdir(blockchain_dir):
         print(f"❌ Error: 'blockchain' directory not found at expected location: {blockchain_dir}")
         return False

    # --- MODIFICATION HERE: Removed '; Pause' ---
    argument_string = (
        f"'cd {blockchain_dir}; "
        f"fnm env --use-on-cd --shell powershell | Out-String | Invoke-Expression; "
        f"truffle migrate --network development --reset'" # Removed '; Pause' from the end
    )
    command_list = [
        "powershell", "-Command",
        "Start-Process", "powershell",
        "-ArgumentList", argument_string
    ]
    # --- END MODIFICATION ---

    try:
        deployment_process = subprocess.Popen(command_list)
        # This sleep is CRITICAL - it gives time for truffle migrate AND the .env update to finish
        print("   Waiting for deployment and .env update to complete (approx 25s)...")
        time.sleep(25) # Adjust if needed, but crucial for automation
        print("✅ Smart contract deployment process finished (check background window for errors if issues arise).")
        return True # Indicate deployment process was started and waited for
    except FileNotFoundError:
        print("❌ Error: 'powershell', 'fnm', or 'truffle' command not found.")
        return False
    except Exception as e:
        print(f"❌ Error initiating deployment: {e}")
        return False

def start_smart_grid():
    print("🟡 Starting Smart-Grid in a new PowerShell window...")
    spade_process = subprocess.Popen(["powershell", "-Command", "Start-Process", "powershell", "-ArgumentList 'python smart_grid.py'"])
    time.sleep(2)
    print("✅ Smart-Grid started in a separate window!")
    return spade_process

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
    smart_grid_process = start_smart_grid() # Simulate neighbours on the Smart-Grid

    print("🟡 Running Multi-Agent System...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Shutting down processes...")
        spade_process.terminate()
        streamlit_process.terminate()
        ganache_process.terminate()
        deployment_process.terminate()
        print("✅ Cleanup complete. Exiting.")
