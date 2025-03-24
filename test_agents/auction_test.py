from web3 import Web3
import json
import time
import hashlib
import os

# Connect to local blockchain (Ganache)
web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
assert web3.is_connected(), "Failed to connect to the blockchain"

# Update contract address each time you recompile and deploy
contract_address = "0x1354E19699CD67Aa54E1383d79454fcae1C4C6Ad"

# Ensure the contract is deployed
code = web3.eth.get_code(contract_address)
assert code != b'0x', "Contract address is invalid or the contract is not deployed."

# Load the contract ABI dynamically
project_dir = os.path.abspath(os.path.join(os.getcwd(), ".."))
contract_path = os.path.join(project_dir, "blockchain", "build", "contracts", "EnergyVickreyAuction.json")

with open(contract_path, "r") as abi_file:
    contract_data = json.load(abi_file)

# Validate ABI structure
if 'abi' not in contract_data or not isinstance(contract_data['abi'], list):
    raise ValueError("ABI is missing or invalid in the contract JSON file.")

contract_abi = contract_data['abi']
print(f"Ganache connected: {web3.is_connected()}")

# Initialize the contract
auction_contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# Define bidder accounts (from Ganache)
accounts = web3.eth.accounts
bidder1, bidder2 = accounts[1], accounts[2]

# Function to create a sealed bid hash
def create_sealed_bid(value, nonce):
    bid_hash = hashlib.sha256(f"{value}{nonce}".encode()).hexdigest()
    return "0x" + bid_hash  # Solidity expects a 0x-prefixed hex string

# Step 1: Bidders place sealed bids
bid_value_1 = web3.to_wei(0.01, "ether")
bid_value_2 = web3.to_wei(0.05, "ether")
nonce_1 = "random123"
nonce_2 = "secure456"

sealed_bid_1 = create_sealed_bid(bid_value_1, nonce_1)
sealed_bid_2 = create_sealed_bid(bid_value_2, nonce_2)

tx1 = auction_contract.functions.bid(sealed_bid_1).transact({
    "from": bidder1,
    "value": bid_value_1,
    "gas": 3000000
})

tx2 = auction_contract.functions.bid(sealed_bid_2).transact({
    "from": bidder2,
    "value": bid_value_2,
    "gas": 3000000
})

web3.eth.wait_for_transaction_receipt(tx1)
web3.eth.wait_for_transaction_receipt(tx2)

print("Bids submitted!")

# Wait for bidding phase to end (simulation)
print("Waiting for bidding phase to end...")
time.sleep(10)

# Step 2: Reveal bids (encode nonce properly)
nonce_1_bytes32 = Web3.to_bytes(text=nonce_1).ljust(32, b'\x00')  # Convert to bytes32
nonce_2_bytes32 = Web3.to_bytes(text=nonce_2).ljust(32, b'\x00')  # Convert to bytes32

tx3 = auction_contract.functions.reveal(bid_value_1, nonce_1_bytes32).transact({
    "from": bidder1,
    "gas": 3000000
})

tx4 = auction_contract.functions.reveal(bid_value_2, nonce_2_bytes32).transact({
    "from": bidder2,
    "gas": 3000000
})

web3.eth.wait_for_transaction_receipt(tx3)
web3.eth.wait_for_transaction_receipt(tx4)

print("Bids revealed!")

# Step 3: Finalize the auction
print("Finalizing auction...")
tx5 = auction_contract.functions.finalizeAuction().transact({
    "from": accounts[0],  # Auctioneer finalizes
    "gas": 3000000
})
web3.eth.wait_for_transaction_receipt(tx5)

# Get auction results
winner = auction_contract.functions.highestBidder().call()
final_price_wei = auction_contract.functions.secondHighestBid().call()
final_price_eth = web3.from_wei(final_price_wei, "ether")
print(f"Auction Winner: {winner} with price: {final_price_eth} ETH")
