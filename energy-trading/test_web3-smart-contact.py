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
def test_create_trade(energy_for_sale, price_per_kwh):  
    """Creates a trade on the blockchain."""
    # Build the transaction for creating a trade (10 kWh at 1 CAD)
    tx = contract.functions.createTrade(energy_for_sale, price_per_kwh).build_transaction({
        "from": account.address,  # Sender's Ethereum address
        "gas": 2000000,  # Gas limit
        "gasPrice": web3.to_wei("10", "gwei"),  # Gas price in gwei
        "nonce": web3.eth.get_transaction_count(account.address),  # Ensure transaction uniqueness
    })

    # Sign the transaction with the private key
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    # Send the transaction to the Ethereum network
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    print("✅ Trade Created. TX Hash:", web3.to_hex(tx_hash))
    
    # Wait for the transaction to be mined
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction receipt:", tx_receipt)
    return tx_receipt

# Function to Get Trade Details
def test_get_trade(trade_id):
    """Retrieves trade details from the blockchain."""
    try:
        # Fetch trade details from the contract
        trade = contract.functions.getTrade(trade_id).call()
        print(f"ℹ️ Trade {trade_id}: Seller={trade[0]}, Buyer={trade[1]}, Energy={trade[2]} kWh, Price={trade[3]} CAD, Completed={trade[4]}")
    except Exception as e:
        print(f"Error retrieving trade {trade_id}: {e}")

# Function to Accept a Trade
def test_accept_trade(trade_id, price):
    """Accepts a trade and transfers payment."""
    
    # Check the account balance before sending the transaction
    balance = web3.eth.get_balance(account.address)
    print(f"Account balance: {web3.from_wei(balance, 'ether')} ETH")

    # Estimate the gas cost for the transaction
    gas_estimate = contract.functions.acceptTrade(trade_id).estimate_gas({
        "from": account.address,
        "value": web3.to_wei(str(price), "ether"),
    })

    total_gas_cost = gas_estimate * web3.to_wei("10", "gwei")  # Gas price is 10 gwei
    
    print(f"Estimated Gas Cost: {web3.from_wei(total_gas_cost, 'ether')} ETH")
    
    # Ensure the account has enough funds to cover gas and value
    total_cost = total_gas_cost + web3.to_wei(str(price), "ether")
    if balance < total_cost:
        raise ValueError("Insufficient funds to complete the transaction. Please ensure your account has enough ETH for gas and value.")

    # Build the transaction to accept a trade
    tx = contract.functions.acceptTrade(trade_id).build_transaction({
        "from": account.address,  # Buyer's Ethereum address
        "value": web3.to_wei(str(price), "ether"),  # Convert price to wei and send as payment
        "gas": gas_estimate,  # Gas limit from estimate
        "gasPrice": web3.to_wei("10", "gwei"),  # Gas price
        "nonce": web3.eth.get_transaction_count(account.address),  # Unique transaction number
    })

    # Sign the transaction with the private key
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    # Send the transaction to the Ethereum network
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    print("✅ Trade Accepted. TX Hash:", web3.to_hex(tx_hash))

# Run Tests
# Create a trade (10 kWh at 1 CAD)# note: no float values in solidity
tx_receipt = test_create_trade(10, 1)

# After creating a trade, extract the trade ID from the event logs or tx receipt
trade_id = 0  # Or extract the trade ID from tx_receipt based on your contract logic

# Retrieve details of the first trade
test_get_trade(trade_id)

# Accept the first trade for 1 CAD
test_accept_trade(trade_id, 1)
