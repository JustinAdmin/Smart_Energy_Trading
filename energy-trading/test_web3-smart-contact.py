from web3 import Web3
import json
import os
from dotenv import load_dotenv  # pip install python-dotenv

# Load environment variables from .env file
load_dotenv()

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
with open("artifacts/contracts/EnergyTrading.sol/EnergyTrading.json") as f:
    contract_json = json.load(f)
    contract_abi = contract_json["abi"]

# Instantiate the smart contract object
contract = web3.eth.contract(address=DEPLOYED_CONTRACT_ADDRESS, abi=contract_abi)

# Function to Get the Latest Trade ID
def get_latest_trade_id():
    return contract.functions.getTradesLength().call() - 1  # Get the last trade index

# Function to Create a Trade
def test_create_trade(energy_for_sale, price_per_kwh):  
    """Creates a trade on the blockchain."""
    tx = contract.functions.createTrade(energy_for_sale, price_per_kwh).build_transaction({
        "from": account.address,
        "gas": gwei_gas_limit,
        "gasPrice": web3.to_wei(gwei_gas_fee, "gwei"),
        "nonce": web3.eth.get_transaction_count(account.address),
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    print("✅ Trade Created. TX Hash:", web3.to_hex(tx_hash))
    
    return get_latest_trade_id()

# Function to Get Trade Details
def test_get_trade(trade_id):
    """Retrieves trade details from the blockchain."""
    trade = contract.functions.getTrade(trade_id).call()
    print(f"ℹ️ Trade {trade_id}: Seller={trade[0]}, Buyer={trade[1]}, Energy={trade[2]} kWh, Price={trade[3]} CAD, Completed={trade[4]}")
    return trade[3]  # Return price for use in accept_trade

# Function to Accept a Trade at the Listed Price
def test_accept_trade(trade_id):
    """Accepts a trade and transfers payment at the listed price."""
    trade_price = test_get_trade(trade_id)  # Fetch the exact trade price from the blockchain
    
    balance = web3.eth.get_balance(account.address)
    total_cost = web3.to_wei(str(trade_price), "ether")
    
    if balance < total_cost:
        raise ValueError("Insufficient funds to complete the transaction. Ensure your account has enough ETH for gas and value.")

    tx = contract.functions.acceptTrade(trade_id).build_transaction({
        "from": account.address,
        "value": total_cost,
        "gas": gwei_gas_limit,
        "gasPrice": web3.to_wei(gwei_gas_fee, "gwei"),
        "nonce": web3.eth.get_transaction_count(account.address),
    })
    
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    print("✅ Trade Accepted. TX Hash:", web3.to_hex(tx_hash))

# Run Tests
latest_trade_id = test_create_trade(10, 1)  # Create a trade (10 kWh at 1 CAD)
test_accept_trade(latest_trade_id)  # Accept the trade at the listed price
