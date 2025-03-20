from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
# from web3 import Web3
import json
# import os
# from dotenv import load_dotenv  # pip install python-dotenv
import asyncio

'''
# Load environment variables from .env file
# Load .env file from a different folder (e.g., "config" folder)
dotenv_path = os.path.join("energy-trading", ".env")
load_dotenv(dotenv_path)

# Get the absolute path of the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
print(f"Project Root: {project_root}")
# Construct the full path to the contract JSON file
contract_path = os.path.join(project_root, "energy-trading", "artifacts", "contracts", "EnergyTrading.sol", "EnergyTrading.json")
print(f"Contract Path: {contract_path}")
# Set gas fee parameters
gwei_gas_fee = 1  # Lower gas price for reduced costs
gwei_gas_limit = 500000  # Lower gas limit to optimize fees

# Fetch the private key and API key from environment variables
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
DEPLOYED_CONTRACT_ADDRESS = os.getenv("DEPLOYED_CONTRACT_ADDRESS")

# Validate that environment variables are loaded
if not PRIVATE_KEY or not ALCHEMY_API_KEY or not DEPLOYED_CONTRACT_ADDRESS:
    raise ValueError("Missing environment variables! Check your .env file.")

# Correctly format the Alchemy URL
ALCHEMY_URL = f"https://eth-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

# Connect to Ethereum Network via Web3
web3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))

# Verify connection
if not web3.is_connected():
    raise ConnectionError("Failed to connect to the Ethereum network!")

# Load the Ethereum account using the private key
account = web3.eth.account.from_key(PRIVATE_KEY)

# Load Contract ABI (Application Binary Interface) to interact with the smart contract
with open(contract_path) as f:
    contract_json = json.load(f)
    contract_abi = contract_json["abi"]

# Instantiate the smart contract object
contract = web3.eth.contract(address=DEPLOYED_CONTRACT_ADDRESS, abi=contract_abi)

# Function to Get the Latest Trade ID
def get_latest_trade_id():
    return contract.functions.getTradesLength().call() - 1  # Get the last trade index

# Function to Create a Trade on the Blockchain
def create_trade(energy_amount, price):
    """Creates a trade on the blockchain."""
    tx = contract.functions.createTrade(int(energy_amount), int(price)).build_transaction({
        "from": account.address,
        "gas": gwei_gas_limit,
        "gasPrice": web3.to_wei(gwei_gas_fee, "gwei"),
        "nonce": web3.eth.get_transaction_count(account.address),
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    print("✅ Trade Created. TX Hash:", web3.to_hex(tx_hash))
    return web3.to_hex(tx_hash)
'''

# Negotiation Agent: Facilitates peer-to-peer energy trading
class NegotiationAgent(Agent):
    class TradingBehaviour(CyclicBehaviour):
        async def run(self):
            print("[NegotiationAgent] Waiting for surplus energy data...")
            await asyncio.sleep(5)
            msg = await self.receive(timeout=30)
            if msg:
                try:
                    data = json.loads(msg.body).get("house")
                    if data is None:
                        print("[NegotiationAgent] No data received")
                    else:
                        print(f"[NegotiationAgent] Received data: {data}")
                        surplus_energy = data.get("current_production") - data.get("current_demand")

                        # If there is surplus energy, create a trade on the blockchain
                        if surplus_energy > 0:
                            trade_amount = min(surplus_energy, 2.0)  # Trade rule
                            trade_price = trade_amount * 1  # Example pricing rule (1 CAD per kWh)
                            #Note: The trade price should be determined by the Demand agent based on the market conditions
                            
                            # Execute blockchain transaction
                            #tx_hash = create_trade(trade_amount, trade_price)
                            tx_hash = "0x1234567890"
                            print(f"[NegotiationAgent] Created fake trade: {trade_amount} kWh at {trade_price} CAD per kWh")
                            
                            # Send trade confirmation to Facilitating Agent
                            response = Message(to="facilitating@localhost")
                            response.body = json.dumps({"traded_energy": trade_amount, "tx_hash": tx_hash})

                            await self.send(response)
                            print(f"[NegotiationAgent] Sent trade decision to FacilitatingAgent: {response.body}")

                except Exception as e:
                    print(f"[NegotiationAgent] Error: {e}")
                    print(f"[NegotiationAgent] {msg}")

    async def setup(self):
        print("[NegotiationAgent] Started")
        self.add_behaviour(self.TradingBehaviour())
        self.web.start(hostname="localhost", port="9095")
