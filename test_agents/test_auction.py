from web3 import Web3
import json
import time
import hashlib # Not used in current code, but keep if needed elsewhere
import os
import subprocess # Import subprocess
from datetime import datetime
from dotenv import load_dotenv

# --- Functions copied and adapted from main.py ---

def start_ganache():
    """Starts Ganache CLI in a separate PowerShell window."""
    print("🟡 Starting Ganache CLI...")
    try:
        # Using '--networkId 5777' to match truffle config if needed
        ganache_process = subprocess.Popen(["powershell", "-Command", "Start-Process", "powershell", "-ArgumentList 'ganache-cli --networkId 5777'"])
        # Increased sleep time to give Ganache more time to initialize fully
        print("   Waiting for Ganache to initialize...")
        time.sleep(5) # Increased sleep duration
        print("✅ Ganache CLI should be running in a separate window.")
        return ganache_process
    except FileNotFoundError:
        print("❌ Error: 'powershell' or 'ganache-cli' command not found. Ensure they are in your system's PATH.")
        return None
    except Exception as e:
        print(f"❌ Error starting Ganache: {e}")
        return None
    
def deploy_smart_contract():
    """Deploys the smart contract using Truffle in a separate PowerShell window."""
    print("🟡 Deploying the smart contract...")
    project_root = os.path.dirname(os.path.dirname(__file__))
    blockchain_dir = os.path.join(project_root, "blockchain")
    print(f"   Running deployment from project root: {project_root}")
    print(f"   Expecting 'blockchain' directory at: {blockchain_dir}")

    if not os.path.isdir(blockchain_dir):
         print(f"❌ Error: 'blockchain' directory not found at expected location: {blockchain_dir}")
         return False # Changed to False for consistency

    # --- MODIFICATION HERE: Added '; Pause' ---
    argument_string = (
        f"'cd {blockchain_dir}; "
        f"fnm env --use-on-cd --shell powershell | Out-String | Invoke-Expression; "
        f"truffle migrate --network development --reset; " # Ensure no accidental semicolon here
        f"Pause'" # Added Pause command here
    )
    command_list = [
        "powershell", "-Command",
        "Start-Process", "powershell",
        "-ArgumentList", argument_string # Use the formatted string
    ]
    # --- END MODIFICATION ---

    try:
        deployment_process = subprocess.Popen(command_list)
        print("   Waiting for deployment to complete (this may take 20-30 seconds)...")
        # Keep the sleep, as Python continues while the separate window runs
        time.sleep(25)
        print("✅ Smart contract deployment initiated. Check the separate window for status/errors AND PRESS ENTER WHEN DONE.")
        return True
    except FileNotFoundError:
        print("❌ Error: 'powershell', 'fnm', or 'truffle' command not found.")
        return False
    except Exception as e:
        print(f"❌ Error initiating deployment: {e}")
        return False
    

# --- DELAYED INITIALIZATION: Moved Web3 connection and contract loading inside main execution block ---
web3 = None
auction_contract = None
accounts = []
contract_address = None
# --- END DELAYED INITIALIZATION ---


# Function to create a sealed bid hash (same as before)
def create_sealed_bid(value, nonce):
    encoded = Web3.solidity_keccak(['uint256', 'string'], [value, nonce])
    return encoded

# wait_until function (same as before, consider simplifying if needed)
def wait_until(target_timestamp):
    if not target_timestamp or target_timestamp == 0:
         print("   Invalid target timestamp for wait_until.")
         return
    target_dt = datetime.fromtimestamp(target_timestamp)
    current_dt = datetime.now()
    wait_seconds = (target_dt - current_dt).total_seconds()

    if wait_seconds > 0:
        print(f"   Waiting for {wait_seconds:.1f} seconds until {target_dt}...")
        # Use smaller sleep intervals for more responsiveness if needed
        sleep_interval = max(1, wait_seconds / 5) # Sleep in chunks
        while wait_seconds > 0:
             actual_sleep = min(sleep_interval, wait_seconds)
             time.sleep(actual_sleep)
             wait_seconds -= actual_sleep
             # Optional: Add a print statement here if you want updates during wait
        time.sleep(1) # Small buffer after waiting
        print("   Wait finished.")
    else:
         print(f"   Target time {target_dt} already passed, proceeding immediately.")
    return


# Function to run a full auction round (references global web3, auction_contract, accounts)
def run_auction_round():
    global web3, auction_contract, accounts # Ensure we are using the initialized globals
    if not web3 or not auction_contract or not accounts:
        print("❌ Web3 connection, contract, or accounts not initialized. Cannot run auction.")
        return False

    print("\n--- Running New Auction Round ---")
    # Bidders selected from available accounts (excluding account 0, the seller/deployer)
    bidders = accounts[1:5] # Assuming at least 5 accounts exist
    if len(accounts) < 5:
         print("⚠️ Warning: Fewer than 5 accounts available in Ganache. Adjusting bidder count.")
         bidders = accounts[1:]
         if not bidders:
              print("❌ Error: No bidder accounts available (only account 0 found).")
              return False

    print(f"Seller/Deployer: {accounts[0]}")
    print(f"Bidders: {bidders}")

    # Step 1: Start the auction (using account 0)
    try:
        current_bidding_start = auction_contract.functions.biddingStart().call()
        current_reveal_end = auction_contract.functions.revealEnd().call()
        now = time.time()

        if current_bidding_start == 0 or now > current_reveal_end:
            print("   Starting new auction...")
            energy_amount = 5 # Example amount
            # Load durations from .env (should be updated by migration script)
            bidding_duration = int(os.getenv("BIDDING_TIME", 20)) # Default if not in .env
            reveal_duration = int(os.getenv("REVEAL_TIME", 10)) # Default if not in .env

            tx_hash = auction_contract.functions.startAuction(energy_amount).transact({
                'from': accounts[0],
                'gas': 3000000, # Adjust gas if needed
                'gasPrice': web3.to_wei('20', 'gwei')
            })
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"   Auction started successfully! Tx: {receipt.transactionHash.hex()}")
            print(f"   (Using BIDDING_TIME={bidding_duration}, REVEAL_TIME={reveal_duration} from .env)")
        else:
            print("   Auction already in progress. Joining current round.")

    except Exception as e:
        print(f"❌ Error starting auction: {e}")
        return False # Stop if auction can't be started/verified


    # Step 2 & 3: Wait for bidding phase and Place bids
    try:
        bidding_start_ts = auction_contract.functions.biddingStart().call()
        bidding_end_ts = auction_contract.functions.biddingEnd().call()
        print(f"   Bidding phase: {datetime.fromtimestamp(bidding_start_ts)} -> {datetime.fromtimestamp(bidding_end_ts)}")

        wait_until(bidding_start_ts) # Wait for phase to start if needed

        if time.time() < bidding_end_ts:
             print("   Placing bids...")
             # Ensure bid values match number of bidders
             bid_values_eth = [0.1, 0.2, 0.15, 0.25]
             nonces = ["test_house1", "test_house2", "test_house3", "test_house4"] # Unique nonces

             if len(bidders) < len(bid_values_eth):
                 print(f"   Adjusting bids/nonces to match {len(bidders)} bidders.")
                 bid_values_eth = bid_values_eth[:len(bidders)]
                 nonces = nonces[:len(bidders)]

             bid_values_wei = [web3.to_wei(v, "ether") for v in bid_values_eth]
             sealed_bids = [create_sealed_bid(bid_values_wei[i], nonces[i]) for i in range(len(bid_values_wei))]

             for i, bidder in enumerate(bidders):
                 if time.time() >= bidding_end_ts:
                     print("   Bidding time ended during bid placement.")
                     break
                 try:
                     tx_hash = auction_contract.functions.bid(sealed_bids[i]).transact({
                         "from": bidder,
                         "value": bid_values_wei[i], # Sending bid value as deposit
                         "gas": 3000000
                     })
                     receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
                     print(f"     Bid placed by {bidder[:10]}... Tx: {receipt.transactionHash.hex()}")
                 except Exception as e:
                     # Handle common errors like "bidder already bid" gracefully
                     if "Bidder has already placed a bid" in str(e):
                          print(f"     Bid already placed by {bidder[:10]}...")
                     else:
                          print(f"     ❌ Failed to place bid for {bidder[:10]}...: {e}")
                 time.sleep(1) # Small delay between bids

             print("   Finished placing bids.")
        else:
             print("   Bidding phase already ended.")

    except Exception as e:
        print(f"❌ Error during bidding phase: {e}")
        # Decide whether to continue or return False based on severity

    # Step 4 & 5: Wait for reveal phase and Reveal bids
    try:
        reveal_start_ts = auction_contract.functions.biddingEnd().call() # Reveal starts when bidding ends
        reveal_end_ts = auction_contract.functions.revealEnd().call()
        print(f"   Reveal phase: {datetime.fromtimestamp(reveal_start_ts)} -> {datetime.fromtimestamp(reveal_end_ts)}")

        wait_until(reveal_start_ts) # Wait for reveal phase to start

        if time.time() < reveal_end_ts:
            print("   Revealing bids...")
            # Refresh bidder list in case some failed to bid
            current_bidders = []
            try:
                 # Use the getBidders view function if it exists and works
                 current_bidders = auction_contract.functions.getBidders().call()
                 print(f"   Bidders retrieved from contract: {len(current_bidders)}")
                 if not current_bidders: # Fallback if getBidders fails or returns empty
                     current_bidders = bidders # Use the list we tried to bid with
                     print("   Warning: Using initial bidder list for reveal (getBidders empty/failed).")

            except Exception as e:
                 print(f"   Warning: Failed to call getBidders(): {e}. Using initial bidder list.")
                 current_bidders = bidders # Fallback

            # Match bidders to their original bid values/nonces (requires consistent ordering or a mapping)
            # This assumes the order in `bidders` corresponds to `bid_values_wei` and `nonces`
            bidder_map = {b: i for i, b in enumerate(bidders)} # Map original bidders to index

            for bidder_addr in current_bidders:
                 if time.time() >= reveal_end_ts:
                     print("   Reveal time ended during reveal process.")
                     break
                 if bidder_addr in bidder_map:
                     bid_index = bidder_map[bidder_addr]
                     try:
                         tx_hash = auction_contract.functions.reveal(bid_values_wei[bid_index], nonces[bid_index]).transact({
                             'from': bidder_addr,
                             "gas": 3000000
                         })
                         receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
                         print(f"     Bid revealed by {bidder_addr[:10]}... Tx: {receipt.transactionHash.hex()}")
                     except Exception as e:
                         # Handle common errors like "no unrevealed bid" or hash mismatch
                         if "No unrevealed bid" in str(e):
                              print(f"     No unrevealed bid found for {bidder_addr[:10]}...")
                         elif "Invalid bid reveal" in str(e):
                              print(f"     Reveal failed (hash mismatch?) for {bidder_addr[:10]}...")
                         else:
                              print(f"     ❌ Failed to reveal bid for {bidder_addr[:10]}...: {e}")
                 else:
                      print(f"   Warning: Bidder {bidder_addr[:10]}... from contract list not found in original test list.")

                 time.sleep(1) # Small delay

            print("   Finished revealing bids.")
        else:
             print("   Reveal phase already ended.")

    except Exception as e:
        print(f"❌ Error during reveal phase: {e}")


    # Step 6: Wait for close phase and Close the auction
    try:
        reveal_end_ts = auction_contract.functions.revealEnd().call()
        print(f"   Close possible after: {datetime.fromtimestamp(reveal_end_ts)}")
        wait_until(reveal_end_ts) # Wait until closing is allowed

        is_ended = auction_contract.functions.ended().call()
        if not is_ended:
             print("   Closing auction...")
             try:
                 tx_hash = auction_contract.functions.closeAuction().transact({
                     "from": accounts[0], # Seller closes
                     "gas": 3000000
                 })
                 receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
                 print(f"   Auction closed successfully! Tx: {receipt.transactionHash.hex()}")

                 # Check results after closing
                 winner = auction_contract.functions.highestBidder().call()
                 final_price_wei = auction_contract.functions.secondHighestBid().call()
                 final_price_eth = web3.from_wei(final_price_wei, "ether")
                 energy = auction_contract.functions.energyAmount().call()
                 print(f"   --- Auction Results ---")
                 print(f"   Winner: {winner}")
                 print(f"   Energy: {energy} kWh")
                 print(f"   Winning Price (2nd Bid): {final_price_eth} ETH ({final_price_wei} Wei)")
                 print(f"   -----------------------")
                 return True # Indicate successful round

             except Exception as e:
                 print(f"   ❌ Failed to close auction: {e}")
                 return False # Indicate failure
        else:
             print("   Auction already closed.")
             return True # Auction was already closed, consider this round "done"

    except Exception as e:
        print(f"❌ Error during closing phase: {e}")
        return False # Indicate failure


# Function to reset auction (references global web3, auction_contract, accounts)
# Note: This might not be strictly needed if startAuction handles resets,
# but keeping it as requested by user.
def reset_auction():
    global web3, auction_contract, accounts
    if not web3 or not auction_contract or not accounts:
        print("❌ Web3 connection, contract, or accounts not initialized. Cannot reset.")
        return False

    print("\n--- Resetting Auction for Next Round ---")
    try:
        is_ended = auction_contract.functions.ended().call()
        if not is_ended:
             print("   Warning: Auction not closed before reset. Attempting reset anyway.")

        # Load durations from .env for reset command
        bidding_time = int(os.getenv("BIDDING_TIME", 20))
        reveal_time = int(os.getenv("REVEAL_TIME", 10))

        tx_hash = auction_contract.functions.resetAuction(bidding_time, reveal_time).transact({
            "from": accounts[0], # Assuming seller (account 0) resets
            "gas": 3000000
        })
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"   Auction reset successfully! Tx: {receipt.transactionHash.hex()}")
        print(f"   Next round will use BIDDING_TIME={bidding_time}, REVEAL_TIME={reveal_time}")
        return True

    except Exception as e:
        print(f"   ❌ Failed to reset auction: {e}")
        # Check if error indicates auction wasn't closed first
        if "Auction must be closed first" in str(e):
            print("   (Auction needs to be closed before reset can be called)")
        return False


# Main test execution loop
def run_tests(rounds=2):
    print(f"\n=== Starting Auction Test ({rounds} Rounds) ===")
    successful_rounds = 0
    for i in range(rounds):
        print(f"\n>>> Round {i + 1} / {rounds} <<<")
        round_success = run_auction_round()

        if round_success:
            successful_rounds += 1
            # Optional: Reset only if round was successful?
            # reset_success = reset_auction()
            # if not reset_success:
            #     print("❌ Failed to reset after successful round. Stopping.")
            #     break
            # Adding a delay before the next round starts
            delay_before_next = int(os.getenv("NEXT_ROUND_DELAY", 5)) # Use env var or default
            print(f"\n--- Waiting {delay_before_next}s before potentially starting next round ---")
            time.sleep(delay_before_next)
        else:
            print(f"❌ Auction Round {i+1} failed. Stopping test.")
            break # Stop if a round fails

        # Removed explicit reset call here - let startAuction handle it
        # reset_auction() # Call reset function if needed between rounds

    print(f"\n=== Auction Test Finished ===")
    print(f"   Successfully completed {successful_rounds} / {rounds} rounds.")


# Main script execution block
if __name__ == "__main__":
    ganache_process = None
    deployment_success = False

    try:
        # 1. Start Ganache
        ganache_process = start_ganache()
        if not ganache_process:
            raise Exception("Ganache failed to start. Exiting.")

 # 2. Deploy Contract
        deployment_success = deploy_smart_contract()
        if not deployment_success:
            # If initiation failed, stop
             raise Exception("Deployment initiation failed or error occurred. Exiting.")
        print("   Deployment process finished. Proceeding with script.")

        # 3. Initialize Web3 and Contract (AFTER Ganache start and deployment initiation)
        print("🟡 Initializing Web3 connection...")
        web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
        if not web3.is_connected():
             print("❌ Failed to connect to Ganache after starting it. Check Ganache window.")
             raise ConnectionError("Failed to connect to Web3 provider.")
        print("✅ Web3 connected to Ganache.")

        accounts = web3.eth.accounts
        if not accounts:
             print("❌ No accounts found on Ganache. Ensure it's running correctly.")
             raise ValueError("No accounts available.")
        print(f"   Found {len(accounts)} accounts.")

        print("🟡 Loading contract...")
        # Load environment variables from the .env file (needs to be updated by deployment)
        load_dotenv() # Load default .env first
        project_dir = os.path.dirname(os.path.abspath(__file__)) # Get dir of this script
        # Assuming blockchain folder is relative to this script's location
        blockchain_parent_dir = os.path.dirname(project_dir) # Go up one level from script dir if needed
        env_path = os.path.join(blockchain_parent_dir, "blockchain", ".env")
        print(f"   Looking for .env at: {env_path}")
        if load_dotenv(dotenv_path=env_path, override=True): # Load specific .env, override others
             print("   Loaded .env file from blockchain directory.")
        else:
             print("   Warning: blockchain/.env file not found or failed to load.")
             # Attempt to load CONTRACT_ADDRESS anyway in case it's in default .env
        contract_address = os.getenv("CONTRACT_ADDRESS")
        if not contract_address:
            print("❌ CONTRACT_ADDRESS not found in environment variables after deployment.")
            print("   Ensure the Truffle migration script correctly writes to blockchain/.env")
            raise ValueError("Contract address missing.")
        print(f"   Using Contract Address: {contract_address}")

        # Ensure the contract bytecode exists at the address
        try:
             code = web3.eth.get_code(contract_address)
             if code == b'0x' or code == b'':
                  print(f"❌ No contract bytecode found at address {contract_address} on network.")
                  print(f"   Deployment likely failed or address in .env is incorrect.")
                  raise ValueError("Contract not deployed at address.")
             print("   Contract bytecode found at address.")
        except Exception as e:
             print(f"❌ Error checking contract code: {e}")
             raise

        # Load the contract ABI
        contract_build_path = os.path.join(blockchain_parent_dir, "blockchain", "build", "contracts", "EnergyVickreyAuction.json")
        print(f"   Loading ABI from: {contract_build_path}")
        try:
            with open(contract_build_path, "r") as abi_file:
                contract_data = json.load(abi_file)
            if 'abi' not in contract_data or not isinstance(contract_data['abi'], list):
                raise ValueError("ABI is missing or invalid in the contract JSON file.")
            contract_abi = contract_data['abi']
            print("   Contract ABI loaded.")
        except FileNotFoundError:
             print(f"❌ ABI file not found at {contract_build_path}.")
             print(f"   Ensure contract compiled successfully.")
             raise
        except Exception as e:
             print(f"❌ Error loading ABI: {e}")
             raise


        # Initialize the contract object
        auction_contract = web3.eth.contract(address=contract_address, abi=contract_abi)
        print("✅ Contract object initialized.")


        # 4. Run the main test logic
        run_tests(rounds=2) # Run specified number of rounds

    except (Exception, KeyboardInterrupt) as e:
        print(f"\n--- An error occurred or script interrupted: {e} ---")

    finally:
        # 5. Cleanup - Attempt to stop Ganache
        print("\n--- Cleaning up ---")
        if ganache_process:
            print("   Terminating Ganache CLI process...")
            try:
                # Use terminate first, then kill if needed
                ganache_process.terminate()
                ganache_process.wait(timeout=5) # Wait a bit for termination
                print("   Ganache terminated.")
            except subprocess.TimeoutExpired:
                print("   Ganache did not terminate gracefully, killing...")
                ganache_process.kill()
                print("   Ganache killed.")
            except Exception as e:
                print(f"   Error stopping Ganache: {e}")
        else:
            print("   No Ganache process to stop (was it started manually?).")

        print("--- Script finished ---")