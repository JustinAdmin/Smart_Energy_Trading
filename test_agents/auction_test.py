from web3 import Web3
import json
import time
import hashlib

# Connect to local blockchain (Ganache)
web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
assert web3.is_connected(), "Failed to connect to blockchain"

# Load contract details
contract_address = "0xE889bbAE4624d0191b9F97446C17754610d41082"  # Replace with deployed contract address
with open("build\contracts\EnergyVickreyAuction.json", "r") as abi_file:
    contract_abi = json.load(abi_file)

auction_contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# Define bidder accounts (from Ganache)
accounts = web3.eth.accounts
bidder1, bidder2 = accounts[1], accounts[2]

# Function to create a sealed bid hash
def create_sealed_bid(value, nonce):
    bid_hash = hashlib.sha256(f"{value}{nonce}".encode()).hexdigest()
    return "0x" + bid_hash  # Solidity expects 0x-prefixed hex

# Step 1: Bidders place sealed bids
bid_value_1, nonce_1 = 50, "random123"
bid_value_2, nonce_2 = 75, "secure456"

sealed_bid_1 = create_sealed_bid(bid_value_1, nonce_1)
sealed_bid_2 = create_sealed_bid(bid_value_2, nonce_2)

tx1 = auction_contract.functions.bid(sealed_bid_1).transact({"from": bidder1, "value": bid_value_1})
tx2 = auction_contract.functions.bid(sealed_bid_2).transact({"from": bidder2, "value": bid_value_2})

web3.eth.wait_for_transaction_receipt(tx1)
web3.eth.wait_for_transaction_receipt(tx2)

print("Bids submitted!")

# Wait for bidding phase to end (simulation)
time.sleep(10)

# Step 2: Reveal bids
tx3 = auction_contract.functions.reveal(bid_value_1, nonce_1).transact({"from": bidder1})
tx4 = auction_contract.functions.reveal(bid_value_2, nonce_2).transact({"from": bidder2})

web3.eth.wait_for_transaction_receipt(tx3)
web3.eth.wait_for_transaction_receipt(tx4)

print("Bids revealed!")

# Step 3: Finalize the auction
tx5 = auction_contract.functions.finalizeAuction().transact({"from": accounts[0]})  # Auctioneer finalizes
web3.eth.wait_for_transaction_receipt(tx5)

# Get auction results
winner = auction_contract.functions.highestBidder().call()
final_price = auction_contract.functions.secondHighestBid().call()
print(f"Auction Winner: {winner} with price: {final_price} ETH")
