from web3 import Web3
import json
import time
import hashlib
import os
from datetime import datetime
from dotenv import load_dotenv
from math import sin

# Load contract address dynamically
project_dir = os.path.dirname(os.path.dirname(__file__))  # Correct path logic

env_path = os.path.join(project_dir, "5014-Project", "blockchain", ".env")

load_dotenv(env_path)  # Ensure .env is loaded from the correct location

# Function to create a sealed bid hash
def create_sealed_bid(value, nonce):
    # Change to match contract's keccak256(abi.encodePacked()) format
    encoded = Web3.solidity_keccak(['uint256', 'string'], [int(value), str(nonce)])
    return encoded

def start_auction(auctioneer, auction_contract, web3, energy_amount=5):
    # Wait for the last auction to end and then start a new one
    try: 
        auction_started = auction_contract.functions.biddingStart().call()
    except Exception as e:
        print(e)
        input("Press Enter to Exit...")
    
    while auction_started != 0:
        auction_started = auction_contract.functions.biddingStart().call()
    
    # Once auction_started is 0 start the auction
    bidding_duration = int(os.getenv("BIDDING_TIME")) 
    reveal_duration = int(os.getenv("REVEAL_TIME"))  
    tx = auction_contract.functions.startAuction(int(energy_amount)).transact({
        'from': auctioneer,
        'gas': 3000000,
        'gasPrice': web3.to_wei('20', 'gwei')
    })
    web3.eth.wait_for_transaction_receipt(tx)
    print(f"Auction started with bidding duration {bidding_duration} and reveal duration {reveal_duration}!")

def wait_until(end_timestamp):
    end_datetime = datetime.fromtimestamp(end_timestamp)
    
    diff = (end_datetime - datetime.now()).total_seconds()
    print(f"Wait time of: {diff}")
    while diff > 1:
        
        diff = (end_datetime - datetime.now()).total_seconds()
        print(f'Time Until Continue: {diff}')
        time.sleep(diff / 2)

def wait_until_timeout(end_timestamp, auction_contract):
    countdown = 3
    while countdown > 0 and end_timestamp == 0:
        print(f"Countdown: {countdown}")
        if end_timestamp == 0:
            time.sleep(3)
            end_timestamp = auction_contract.functions.biddingStart().call()
        countdown -= 1

    if countdown == end_timestamp:
        return True

    wait_until(end_timestamp)
    
    return False
    

# Function to run a full auction round
def run_auction_round(bidders, auction_contract, auctioneer, web3, auction_holder=True, energy_amount=5):
    print("Running new auction round...")

    if auction_holder:
        # Start the auction (if not started)
        start_auction(auctioneer, auction_contract, web3, energy_amount)

    # Step 2: Wait for the bidding phase to open
    bidding_start = auction_contract.functions.biddingStart().call()
    flag = wait_until_timeout(bidding_start, auction_contract)
    if flag:
        start_auction(auctioneer, auction_contract, web3, energy_amount)
    print(f"Bidding phase starts at block time: {datetime.fromtimestamp(bidding_start)}")

    # Step 3: Bidders place sealed bids
    bid_values = [web3.to_wei(0.01, "ether"), web3.to_wei(0.02, "ether"), web3.to_wei(0.015, "ether"), web3.to_wei(0.025, "ether")]
    nonces = ["house1", "house2", "house3", "house4"]

    sealed_bids = [create_sealed_bid(bid_values[i], nonces[i]) for i in range(len(bid_values))]

    bid_delay = int(os.getenv("NEXT_ROUND_DELAY"))  # Configurable delay, default to 5 seconds

    for i, bidder in enumerate(bidders):
        try:
            tx = auction_contract.functions.bid(sealed_bids[i]).transact({
                "from": bidder,
                "value": bid_values[i],
                "gas": 3000000
            })
            web3.eth.wait_for_transaction_receipt(tx)
            print(f"Bid placed by {bidder}")
        except Exception as e:
            print(f"Failed to place bid for {bidder}: {e}")

        # Delay between bids
        time.sleep(bid_delay)

    print("Bids submitted! Moving to reveal phase...")

    # Step 4: Wait for the reveal phase to open
    reveal_start = auction_contract.functions.biddingEnd().call()
    print(f"Reveal phase starts at block time: {datetime.fromtimestamp(reveal_start)}")
    wait_until(reveal_start)
    time.sleep(4)  # Additional delay to ensure all bids are submitted
    
    for i, bidder in enumerate(bidders):
        try:
            tx = auction_contract.functions.reveal(bid_values[i], nonces[i]).transact({
                'from': bidder,
                "gas": 3000000
            })
            receipt = web3.eth.wait_for_transaction_receipt(tx)
            print(f"Bid revealed by {bidder}!")
        except Exception as e:
            print(f"Failed to reveal bid for {bidder}: {e}")
    
    # Calculate winner to display locally
    winner = auction_contract.functions.highestBidder().call()
    final_price_wei = auction_contract.functions.secondHighestBid().call()
    final_price_eth = web3.from_wei(final_price_wei, "ether")
    energy = auction_contract.functions.energyAmount().call()
    print("Bids revealed!")
    reveal_end = auction_contract.functions.revealEnd().call()
    print(f"Reveal ends at block time: {datetime.fromtimestamp(reveal_end)}")
    wait_until(reveal_end)

    # Fetch and display all revealed bids
    print("Fetching all revealed bids...")
    contract_bidders = auction_contract.functions.getBidders().call()
    for contract_bidder in contract_bidders:
        # Access the bid information for each bidder
        bid_info = auction_contract.functions.bids(contract_bidder).call()
        bid_amount_wei = bid_info[1]  # Assuming the deposit is the second element in the returned tuple
        bid_amount_eth = web3.from_wei(bid_amount_wei, 'ether')
        print(f"Bidder: {contract_bidder}, Bid: {bid_amount_eth} ETH")

    # Step 6: Close the auction
    print("Close auction...")
    try:
        
        time.sleep(1)  # Additional delay to ensure all bids are submitted
        tx = auction_contract.functions.closeAuction().transact({
            "from": auctioneer,
            "gas": 3000000
        })
        web3.eth.wait_for_transaction_receipt(tx)
        
        print(f"Auction Winner: {winner} \n Energy: {energy} kWh \n Price: {final_price_eth} ETH")
    except Exception as e:
        print(f"Failed to close auction: {e}")


def reset_auction(auctioneer, auction_contract, web3):
    print("Resetting the auction for the next round...")

    # Get the current time (in seconds) to print when the new auction will end
    current_time = web3.eth.get_block("latest")["timestamp"]

    # Define the new bidding time and reveal time (from environment or default values)
    bidding_time = int(os.getenv("BIDDING_TIME"))  # Configurable or default to 30 seconds
    reveal_time = int(os.getenv("REVEAL_TIME"))  # Configurable or default to 10 seconds

    try:
        # Call the resetAuction function with the bidding and reveal time
        tx_reset = auction_contract.functions.resetAuction(bidding_time, reveal_time).transact({
            "from": auctioneer,  # Auctioneer resets
            "gas": 3000000
        })
        web3.eth.wait_for_transaction_receipt(tx_reset)
        print("Auction reset successfully!")

        # Get the new auction times after resetting
        bidding_end_time = current_time + bidding_time
        reveal_end_time = bidding_end_time + reveal_time

        # Convert to human-readable format (e.g., datetime)
        bidding_end_datetime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(bidding_end_time))
        reveal_end_datetime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(reveal_end_time))

        print(f"Next Auction Bidding Phase ends at: {bidding_end_datetime}")
        print(f"Next Auction Reveal Phase ends at: {reveal_end_datetime}")
    except Exception as e:
        print(f"Failed to reset auction: {e}")




# Main loop for running and resetting auctions on schedule
def main():
    # Connect to local blockchain (Ganache)
    web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
    assert web3.is_connected(), "Failed to connect to the blockchain"

    contract_address = os.getenv("CONTRACT_ADDRESS")
    assert contract_address, "Contract address not found in .env file."

    # Ensure the contract is deployed
    code = web3.eth.get_code(contract_address)
    assert code != b'0x', "Contract address is invalid or the contract is not deployed."

    # Load the contract ABI dynamically
    contract_path = os.path.join(project_dir, "5014-Project", "blockchain", "build", "contracts", "EnergyVickreyAuction.json")

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
    bidders = accounts[2:6]  # Assuming you have 4 bidders, adjust as needed
    auctioneer = accounts[1] # Make the first account for holding auctions
    auction_holder = True
    
    A = 3
    x = 0
    D = 5

    while True:  # Run continuous rounds
        
        try:
            energy_amount = A * sin(x) + D
            x += 0.1

            # Run auction round
            run_auction_round(bidders, auction_contract, auctioneer, web3, auction_holder, energy_amount)
            
            # Flip the status of auction holder and await the next auction.
            auction_holder = not auction_holder

            # Call the reset auction function
            reset_auction(auctioneer, auction_contract, web3)

            # Wait for the next auction to start
            print("Waiting for the next auction round...")
            time.sleep(2)  # Adjust this to the amount of time until the next auction should start
        except Exception as e:
            print(e)
            input("Press Enter to Exit...")

# Start the main loop
main()