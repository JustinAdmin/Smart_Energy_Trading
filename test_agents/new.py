from web3 import Web3
import json
import time
import hashlib

# === CONFIGURATION ===
RPC_URL = "http://127.0.0.1:7545"  # Update if using a testnet
PRIVATE_KEYS = {  
    "auctioneer": "0xYourPrivateKeyHere",  
    "bidder1": "0xBidder1PrivateKeyHere",  
    "bidder2": "0xBidder2PrivateKeyHere"  
}
CONTRACT_ADDRESS = "0xYourContractAddressHere"  # Replace with your deployed contract
GAS_LIMIT = 3000000

# === CONNECT TO BLOCKCHAIN ===
web3 = Web3(Web3.HTTPProvider(RPC_URL))
assert web3.is_connected(), "Failed to connect to blockchain"

# === LOAD CONTRACT ===
with open("EnergyVickreyAuction_abi.json", "r") as abi_file:
    contract_abi = json.load(abi_file)
auction_contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

# === FUNCTION TO CREATE A SEALED BID ===
def create_sealed_bid(value, nonce):
    bid_hash = hashlib.sha256(f"{value}{nonce}".encode()).hexdigest()
    return "0x" + bid_hash  # Solidity expects a 0x-prefixed hex string

# === FUNCTION TO SIGN & SEND TRANSACTION ===
def send_transaction(account, function_call, value=0):
    nonce = web3.eth.get_transaction_count(web3.eth.account.from_key(PRIVATE_KEYS[account]).address)
    txn = function_call.build_transaction({
        "from": web3.eth.account.from_key(PRIVATE_KEYS[account]).address,
        "gas": GAS_LIMIT,
        "gasPrice": web3.eth.gas_price,
        "nonce": nonce,
        "value": value
    })
    signed_txn = web3.eth.account.sign_transaction(txn, PRIVATE_KEYS[account])
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return web3.eth.wait_for_transaction_receipt(tx_hash)

# === STEP 1: PLACE SEALED BIDS ===
bidder1_value, nonce1 = 50, "random123"
bidder2_value, nonce2 = 75, "secure456"

sealed_bid1 = create_sealed_bid(bidder1_value, nonce1)
sealed_bid2 = create_sealed_bid(bidder2_value, nonce2)

print("\n🔹 Submitting sealed bids...")
send_transaction("bidder1", auction_contract.functions.bid(sealed_bid1), bid_value_1)
send_transaction("bidder2", auction_contract.functions.bid(sealed_bid2), bid_value_2)
print("✅ Sealed bids submitted!\n")

# === WAIT FOR BIDDING PHASE TO END (SIMULATION) ===
print("⏳ Waiting for bidding phase to end...\n")
time.sleep(10)

# === STEP 2: REVEAL BIDS ===
print("🔹 Revealing bids...")
send_transaction("bidder1", auction_contract.functions.reveal(bidder1_value, nonce1))
send_transaction("bidder2", auction_contract.functions.reveal(bidder2_value, nonce2))
print("✅ Bids revealed!\n")

# === WAIT FOR REVEAL PHASE TO END (SIMULATION) ===
print("⏳ Waiting for reveal phase to end...\n")
time.sleep(10)

# === STEP 3: FINALIZE AUCTION ===
print("🔹 Finalizing the auction...")
send_transaction("auctioneer", auction_contract.functions.finalizeAuction())
print("✅ Auction finalized!\n")

# === STEP 4: DISPLAY WINNER ===
winner = auction_contract.functions.highestBidder().call()
final_price = auction_contract.functions.secondHighestBid().call()

print(f"🏆 AUCTION RESULTS 🏆")
print(f"Winner: {winner}")
print(f"Final Price Paid: {final_price} ETH\n")
