from web3 import Web3
import json
import os
from dotenv import load_dotenv  # pip install python-dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch the private key
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

# Validate PRIVATE_KEY format
PRIVATE_KEY = PRIVATE_KEY.strip()  # Remove extra spaces
if not all(c in "0123456789abcdefABCDEF" for c in PRIVATE_KEY) or len(PRIVATE_KEY) != 64:
    raise ValueError("Invalid PRIVATE_KEY format! It must be a 64-character hexadecimal string.")

# Load the Ethereum account using the private key
account = web3.eth.account.from_key(PRIVATE_KEY)

# Load Contract ABI (Application Binary Interface) to interact with the smart contract
with open("artifacts/contracts/EnergyTrading.sol/EnergyTrading.json") as f:
    contract_json = json.load(f)
    contract_abi = contract_json["abi"]

# Instantiate the smart contract object
contract = web3.eth.contract(address=DEPLOYED_CONTRACT_ADDRESS, abi=contract_abi)

# Function to Create a Trade
# This function allows a seller to list energy for sale on the blockchain
def test_create_trade():
    """Creates a trade on the blockchain."""
    # Build the transaction for creating a trade (10 kWh at 5 CAD)
    tx = contract.functions.createTrade(10, 5).build_transaction({
        "from": account.address,  # Sender's Ethereum address
        "gas": 2000000,  # Gas limit:A simple ETH transfer costs ~21,000 gas, while smart contract interactions require much more.Setting 2,000,000 gas ensures the transaction doesn't fail due to an insufficient gas limit.
        "gasPrice": web3.to_wei("10", "gwei"),  # Gas price in gwei:The fee per gas unit (denoted in Gwei) that the sender is willing to pay for faster transaction processing.
        "nonce": web3.eth.get_transaction_count(account.address),  # Ensure transaction uniqueness
    })

    # Sign the transaction with the private key
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    # Send the transaction to the Ethereum network
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction) 
    
    print("✅ Trade Created. TX Hash:", web3.to_hex(tx_hash))

# Function to Get Trade Details
# This function retrieves trade information from the blockchain
def test_get_trade(trade_id):
    """Retrieves trade details from the blockchain."""
    # Fetch trade details from the contract
    trade = contract.functions.getTrade(trade_id).call()
    print(f"ℹ️ Trade {trade_id}: Seller={trade[0]}, Buyer={trade[1]}, Energy={trade[2]} kWh, Price={trade[3]} CAD, Completed={trade[4]}")

# Function to Accept a Trade
# This function allows a buyer to accept an existing trade and transfer payment
def test_accept_trade(trade_id, price):
    """Accepts a trade and transfers payment."""
    # Build the transaction to accept a trade, ensuring the correct price is sent
    tx = contract.functions.acceptTrade(trade_id).build_transaction({
        "from": account.address,  # Buyer's Ethereum address
        "value": web3.to_wei(str(price), "ether"),  # Convert price to wei and send as payment
        "gas": 2000000,  # Gas limit
        "gasPrice": web3.to_wei("10", "gwei"),  # Gas price
        "nonce": web3.eth.get_transaction_count(account.address),  # Unique transaction number
    })

    # Sign the transaction with the private key
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    # Send the transaction to the Ethereum network
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)  # ✅ Fixed attribute name
    
    print("✅ Trade Accepted. TX Hash:", web3.to_hex(tx_hash))

# Run Tests
# Create a trade (10 kWh at 5 CAD)
tx_receipt = test_create_trade()

# After creating a trade, extract the trade ID from the event logs or tx receipt
# Let's assume the trade ID is 0 for now (you need to check actual return value)
trade_id = 0  # Or extract the trade ID from tx_receipt based on your contract logic

# Retrieve details of the first trade
test_get_trade(trade_id)# Accept the first trade for 5 CAD

# Accept the first trade for 5 CAD
test_accept_trade(trade_id, 5)  # Buyer pays 5 CAD for the trade
