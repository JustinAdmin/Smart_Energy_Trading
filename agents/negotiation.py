from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.behaviour import PeriodicBehaviour
from spade.template import Template
from spade.message import Message
from web3 import Web3
import json
import os
from dotenv import load_dotenv # pip install python-dotenv
import asyncio
import time # Use time for timestamping
import sqlite3 # Import sqlite3
from datetime import datetime, timedelta

# --- Database Configuration ---
DB_NAME = "energy_data.db" # Use the same DB name
SUMMARY_LOG_INTERVAL = 45 # Log summary every 45 seconds

# --- Helper Function for DB Logging ---
def log_blockchain_event(db_name, timestamp, agent_account, event_type, energy_kwh, price_eth, balance_eth, counterparty=None, status="Success", auction_id=None):
    """Logs blockchain-related events to the database."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO blockchain_log (timestamp, agent_account, event_type, energy_kwh, price_eth, balance_eth, counterparty_address, status, auction_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, agent_account, event_type, energy_kwh, price_eth, balance_eth, counterparty, status, auction_id))
    conn.commit()
    conn.close()

def initialize_blockchain_table(db_name):
    """Creates the blockchain log table if it doesn't exist."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blockchain_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,          -- Unix timestamp
            agent_account TEXT,      -- Agent's ETH address
            event_type TEXT,         -- 'Auction Buy', 'Auction Sell', 'Balance Update', 'Bid', 'Reveal', 'Auction Start'
            energy_kwh REAL,         -- Amount bought/sold (can be NULL)
            price_eth REAL,          -- Price paid/received in ETH (can be NULL)
            balance_eth REAL,        -- Agent's balance *after* the event
            counterparty_address TEXT, -- Winner (if selling), Seller (if known, often contract addr)
            status TEXT,             -- 'Success', 'Failed', 'Pending'
            auction_id INTEGER      -- Optional: If your contract has auction IDs
        )
    """)
    conn.commit()
    conn.close()
    print("[NegotiationAgent] Blockchain log table initialized.")

def initialize_trade_summary_table(db_name):
    """Creates the trade summary table if it doesn't exist."""
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL, total_energy_bought_kwh REAL, total_energy_sold_kwh REAL
            )
        """)
        conn.commit()
        conn.close()
        print("[NegotiationAgent] Trade Summary table initialized.")
    except Exception as e:
        print(f"[NegotiationAgent] ERROR initializing Trade Summary table: {e}")


        
# Negotiation Agent: Facilitates peer-to-peer energy trading
class NegotiationAgent(Agent):
    class TradingBehaviour(CyclicBehaviour):
        async def log_trade_summary(db_name, timestamp, total_bought, total_sold):
            """Logs the cumulative trade summary to the database."""
            try:
                conn = sqlite3.connect(db_name)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO trade_summary (timestamp, total_energy_bought_kwh, total_energy_sold_kwh)
                    VALUES (?, ?, ?)
                """, (timestamp, float(total_bought), float(total_sold)))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[NegotiationAgent] ERROR logging Trade Summary: {e}")
        
        async def call_trade_summary(self):
            try:
                self.log_trade_summary(
                    self.agent.db_name, time.time(),
                    self.agent.total_energy_bought, self.agent.total_energy_sold
                )
            except Exception as e:
                print(f"[NegotiationAgent][Summary] Error during summary log: {e}")

        async def on_start(self):
            # --- Database Initialization ---
            self.db_name = DB_NAME
            initialize_blockchain_table(self.db_name) # Create the table
            initialize_trade_summary_table(self.db_name) # Create the trade summary table
            # --- End Database Init ---

            # Connect to local blockchain (Ganache)
            self.web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
            if not self.web3.is_connected():
                 print("[NegotiationAgent] ERROR: Failed to connect to the blockchain")
                 # Optionally stop the agent or handle the error robustly
                 await self.agent.stop()
                 return
            print(f"[NegotiationAgent] Ganache connected: {self.web3.is_connected()}")


            # Load environment variables from the .env file
            load_dotenv()

            # Load contract address dynamically
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Use abspath for reliability
            env_path = os.path.join(project_dir, "blockchain", ".env")
            load_dotenv(dotenv_path=env_path) # Explicitly provide path

            contract_address = os.getenv("CONTRACT_ADDRESS")
            if not contract_address:
                print("[NegotiationAgent] ERROR: Contract address not found in .env file.")
                await self.agent.stop()
                return

            # Ensure the contract is deployed
            try:
                code = self.web3.eth.get_code(contract_address)
                if code == b'0x' or code == b'':
                     print(f"[NegotiationAgent] ERROR: Contract address {contract_address} is invalid or contract not deployed.")
                     await self.agent.stop()
                     return
            except Exception as e:
                 print(f"[NegotiationAgent] ERROR checking contract code: {e}")
                 await self.agent.stop()
                 return


            # Load the contract ABI dynamically
            contract_path = os.path.join(project_dir, "blockchain", "build", "contracts", "EnergyVickreyAuction.json")
            if not os.path.exists(contract_path):
                print(f"[NegotiationAgent] ERROR: Contract ABI file not found at {contract_path}")
                await self.agent.stop()
                return

            try:
                with open(contract_path, "r") as abi_file:
                    contract_data = json.load(abi_file)
            except json.JSONDecodeError:
                 print(f"[NegotiationAgent] ERROR: Could not decode JSON from ABI file {contract_path}")
                 await self.agent.stop()
                 return

            # Validate ABI structure
            if 'abi' not in contract_data or not isinstance(contract_data['abi'], list):
                print("[NegotiationAgent] ERROR: ABI is missing or invalid in the contract JSON file.")
                await self.agent.stop()
                return

            contract_abi = contract_data['abi']


            # Initialize the contract
            self.auction_contract = self.web3.eth.contract(address=contract_address, abi=contract_abi)

            # Define bidder accounts (from Ganache)
            self.accounts = self.web3.eth.accounts
            if not self.accounts:
                 print("[NegotiationAgent] ERROR: No accounts found in Ganache. Is it running?")
                 await self.agent.stop()
                 return
            self.account = self.accounts[0] # Use the first account as this agent's identity
            print(f"[NegotiationAgent] Using account: {self.account}")

            self.bid_amount = 0 # In Wei for contract calls
            self.nonce = "mainhouse" # Make sure this nonce is unique if multiple bidders use same value

            # --- Initial Balance Log ---
            await self.log_current_balance("Init")
            # --- End Initial Balance Log ---


        async def log_current_balance(self, event_suffix="Update"):
            """Queries and logs the agent's current ETH balance."""
            try:
                balance_wei = self.web3.eth.get_balance(self.account)
                balance_eth = self.web3.from_wei(balance_wei, "ether")
                log_blockchain_event(
                    db_name=self.db_name,
                    timestamp=time.time(),
                    agent_account=self.account,
                    event_type=f"Balance {event_suffix}",
                    energy_kwh=None,
                    price_eth=None,
                    balance_eth=float(balance_eth), # Ensure float for DB
                    counterparty=None,
                    status="Success"
                )
                print(f"[NegotiationAgent] Logged Balance: {balance_eth} ETH")
            except Exception as e:
                print(f"[NegotiationAgent] Failed to query or log balance: {e}")
                # Log failure if possible
                try:
                    log_blockchain_event(
                        db_name=self.db_name,
                        timestamp=time.time(),
                        agent_account=self.account,
                        event_type=f"Balance {event_suffix}",
                        energy_kwh=None, price_eth=None, balance_eth=None,
                        status="Failed"
                    )
                except Exception as log_e:
                    print(f"[NegotiationAgent] Also failed to log balance failure: {log_e}")


        def set_bid_amount(self, price_wei): # Expect Wei
            self.bid_amount = price_wei

        async def create_sealed_bid(self, value_wei, nonce): # Expect Wei
            # Change to match contract's keccak256(abi.encodePacked()) format
            encoded = Web3.solidity_keccak(['uint256', 'string'], [value_wei, nonce])
            return encoded

        async def get_auction_timings(self):
            # Add error handling
            try:
                bidding_start = self.auction_contract.functions.biddingStart().call()
                reveal_start = self.auction_contract.functions.biddingEnd().call() # This is biddingEnd in contract
                reveal_end = self.auction_contract.functions.revealEnd().call()
                return bidding_start, reveal_start, reveal_end
            except Exception as e:
                print(f"[NegotiationAgent] Error getting auction timings: {e}")
                return 0, 0, 0 # Return defaults indicating no active auction / error

        async def wait_until(self, target_timestamp):
            # Simplified wait logic
            if not target_timestamp or target_timestamp == 0:
                print("[NegotiationAgent] Invalid target timestamp for wait_until.")
                return # Don't wait if timestamp is invalid

            target_dt = datetime.fromtimestamp(target_timestamp)
            current_dt = datetime.now()
            wait_seconds = (target_dt - current_dt).total_seconds()

            if wait_seconds > 0:
                print(f"[NegotiationAgent] Waiting for {wait_seconds:.2f} seconds until {target_dt}...")
                await asyncio.sleep(wait_seconds + 1) # Add a small buffer
                print("[NegotiationAgent] Wait finished.")
            else:
                 print("[NegotiationAgent] Target time already passed, proceeding immediately.")
            return

        async def start_auction(self, energy_amount_kwh):
            print(f"[NegotiationAgent] Attempting to start auction for {energy_amount_kwh} kWh...")
            # It seems your contract takes energy amount directly? Assuming it does.
            # If it expects Wei value instead, you'll need conversion logic.
            try:
                # Check if an auction is already running (based on biddingStart time)
                current_bidding_start, _, current_reveal_end = await self.get_auction_timings()
                now = time.time()
                if current_bidding_start != 0 and now < current_reveal_end:
                     print("[NegotiationAgent] Cannot start new auction, another is in progress.")
                     # Maybe log this state?
                     return # Don't start if one is active

                # Now safe to try starting
                # Convert energy_amount_kwh to the unit expected by the contract if necessary
                contract_energy_unit = int(energy_amount_kwh) # Assuming contract takes integer kWh for now

                tx = self.auction_contract.functions.startAuction(contract_energy_unit).transact({
                    'from': self.account,
                    'gas': 3000000,
                    'gasPrice': self.web3.to_wei('20', 'gwei') # Adjust gas as needed
                })
                receipt = self.web3.eth.wait_for_transaction_receipt(tx)
                print(f"[NegotiationAgent] Auction started successfully! Tx: {receipt.transactionHash.hex()}")

                # Log Auction Start event
                await self.log_current_balance("Post-AuctionStart") # Log balance after TX cost
                log_blockchain_event(
                    db_name=self.db_name,
                    timestamp=time.time(),
                    agent_account=self.account,
                    event_type="Auction Start",
                    energy_kwh=energy_amount_kwh,
                    price_eth=None,
                    balance_eth=float(self.web3.from_wei(self.web3.eth.get_balance(self.account), "ether")),
                    counterparty=None,
                    status="Success"
                )
                return True # Indicate success

            except Exception as e:
                print(f"[NegotiationAgent] Failed to start auction: {e}")
                # Log Failure
                await self.log_current_balance("Post-AuctionStartFail")
                log_blockchain_event(
                    db_name=self.db_name,
                    timestamp=time.time(),
                    agent_account=self.account,
                    event_type="Auction Start",
                    energy_kwh=energy_amount_kwh,
                    price_eth=None,
                    balance_eth=float(self.web3.from_wei(self.web3.eth.get_balance(self.account), "ether")), # Log balance even on fail
                    status="Failed"
                )
                return False # Indicate failure


        async def bid(self, price_wei): # Expect Wei
            self.set_bid_amount(price_wei) # Store the bid amount (in Wei)
            print(f"[NegotiationAgent] Attempting to bid {self.web3.from_wei(price_wei, 'ether')} ETH...")
            try:
                sealed_bid = await self.create_sealed_bid(self.bid_amount, self.nonce)
                tx = self.auction_contract.functions.bid(sealed_bid).transact({
                    "from": self.account,
                    "value": self.bid_amount, # The actual value sent with the bid (for deposit)
                    "gas": 3000000 # Adjust gas
                })
                receipt = self.web3.eth.wait_for_transaction_receipt(tx)
                print(f"[NegotiationAgent] Bid placed successfully by {self.account}. Tx: {receipt.transactionHash.hex()}")

                # Log Bid event (balance will decrease due to gas + value sent)
                await self.log_current_balance("Post-Bid")
                log_blockchain_event(
                    db_name=self.db_name,
                    timestamp=time.time(),
                    agent_account=self.account,
                    event_type="Bid",
                    energy_kwh=None, # Energy amount not relevant for bid itself
                    price_eth=float(self.web3.from_wei(self.bid_amount, "ether")), # Log the bid price
                    balance_eth=float(self.web3.from_wei(self.web3.eth.get_balance(self.account), "ether")),
                    status="Success"
                )

            except Exception as e:
                print(f"[NegotiationAgent] Failed to place bid for {self.account}: {e}")
                 # Log Failure
                await self.log_current_balance("Post-BidFail")
                log_blockchain_event(
                    db_name=self.db_name,
                    timestamp=time.time(),
                    agent_account=self.account,
                    event_type="Bid",
                    energy_kwh=None,
                    price_eth=float(self.web3.from_wei(self.bid_amount, "ether")),
                    balance_eth=float(self.web3.from_wei(self.web3.eth.get_balance(self.account), "ether")),
                    status="Failed"
                )


        async def reveal(self):
            print(f"[NegotiationAgent] Attempting to reveal bid: {self.web3.from_wei(self.bid_amount, 'ether')} ETH, Nonce: {self.nonce}")
            try:
                tx = self.auction_contract.functions.reveal(self.bid_amount, self.nonce).transact({
                    'from': self.account,
                    "gas": 3000000 # Adjust gas
                })
                receipt = self.web3.eth.wait_for_transaction_receipt(tx)
                print(f"[NegotiationAgent] Bid revealed successfully by {self.account}! Tx: {receipt.transactionHash.hex()}")

                # Log Reveal event (balance changes due to gas, maybe refund if overbid?)
                await self.log_current_balance("Post-Reveal")
                log_blockchain_event(
                    db_name=self.db_name,
                    timestamp=time.time(),
                    agent_account=self.account,
                    event_type="Reveal",
                    energy_kwh=None,
                    price_eth=float(self.web3.from_wei(self.bid_amount, "ether")), # Log revealed amount
                    balance_eth=float(self.web3.from_wei(self.web3.eth.get_balance(self.account), "ether")),
                    status="Success"
                )

            except Exception as e:
                print(f"[NegotiationAgent] Failed to reveal bid for {self.account}: {e}")
                # Log Failure
                await self.log_current_balance("Post-RevealFail")
                log_blockchain_event(
                    db_name=self.db_name,
                    timestamp=time.time(),
                    agent_account=self.account,
                    event_type="Reveal",
                    energy_kwh=None,
                    price_eth=float(self.web3.from_wei(self.bid_amount, "ether")),
                    balance_eth=float(self.web3.from_wei(self.web3.eth.get_balance(self.account), "ether")),
                    status="Failed"
                )

        async def close(self):
            # Close the auction and log the outcome
            print("[NegotiationAgent] Attempting to close auction...")
            try:
                tx = self.auction_contract.functions.closeAuction().transact({
                    "from": self.account, # Usually only auctioneer or anyone can close? Check contract logic.
                    "gas": 3000000 # Adjust gas
                })
                receipt = self.web3.eth.wait_for_transaction_receipt(tx)
                print(f"[NegotiationAgent] closeAuction transaction successful. Tx: {receipt.transactionHash.hex()}")

                # --- Query Results AFTER closing ---
                # It might take a block for state changes like winner/price to finalize
                await asyncio.sleep(2) # Small delay to allow state update

                winner = self.auction_contract.functions.highestBidder().call()
                final_price_wei = self.auction_contract.functions.secondHighestBid().call() # Vickrey price
                final_price_eth = self.web3.from_wei(final_price_wei, "ether")
                energy_kwh = self.auction_contract.functions.energyAmount().call() # Assuming this returns kWh

                print(f"[NegotiationAgent] Auction Closed Results:")
                print(f"  - Winner: {winner}")
                print(f"  - Energy: {energy_kwh} kWh")
                print(f"  - Final Price (2nd Highest Bid): {final_price_eth} ETH ({final_price_wei} Wei)")

                # --- Log Auction Outcome ---
                await self.log_current_balance("Post-Close") # Log balance after potential payout/refund + gas
                current_balance_eth = float(self.web3.from_wei(self.web3.eth.get_balance(self.account), "ether"))

                event_type = "Auction End" # Generic end event
                log_energy = energy_kwh
                log_price = float(final_price_eth)
                log_counterparty = winner

                # Refine event type based on agent's role (Won/Lost/Sold)
                # We need to know who *started* the auction to determine if this agent was the seller.
                # This info isn't directly stored here, assume for now self.account started if it calls close()
                # Or, more realistically, check if winner == self.account
                if winner == self.account:
                    event_type = "Auction Buy" # This agent won the auction (bought energy)
                elif winner != "0x0000000000000000000000000000000000000000": # Check if there *was* a winner (other than null address)
                    # Assume this agent was the seller if it called close() and didn't win
                    # This assumption might be flawed depending on contract logic (who can call closeAuction)
                    event_type = "Auction Sell"
                else:
                    event_type = "Auction End (No Winner)"
                    log_price = None # No price paid if no winner


                log_blockchain_event(
                    db_name=self.db_name,
                    timestamp=time.time(),
                    agent_account=self.account,
                    event_type=event_type,
                    energy_kwh=log_energy,
                    price_eth=log_price,
                    balance_eth=current_balance_eth,
                    counterparty=log_counterparty if event_type == "Auction Sell" else None, # Log winner only if selling
                    status="Success"
                )
                print(f"[NegotiationAgent] Logged auction outcome: {event_type}")


            except Exception as e:
                print(f"[NegotiationAgent] Failed to close auction or log outcome: {e}")
                # Log Failure
                await self.log_current_balance("Post-CloseFail")
                try:
                     log_blockchain_event(
                        db_name=self.db_name,
                        timestamp=time.time(),
                        agent_account=self.account,
                        event_type="Auction End", # Generic failure event
                        energy_kwh=None, price_eth=None,
                        balance_eth=float(self.web3.from_wei(self.web3.eth.get_balance(self.account), "ether")),
                        status="Failed"
                    )
                except Exception as log_e:
                     print(f"[NegotiationAgent] Also failed to log close failure: {log_e}")


        async def current_auction_state(self, bidding_start, bidding_end, reveal_end):
            # Returns state index: -1 No Auction, 0 Pre-Bidding, 1 Bidding, 2 Reveal, 3 Post-Reveal/Closing
            current_time = time.time() # Use time.time() for consistency with logs

            if bidding_start == 0: # No auction initialized or last one fully ended
                print("[NegotiationAgent] State: No active auction.")
                return -1
            elif current_time < bidding_start:
                print(f"[NegotiationAgent] State: Pre-Bidding (Starts at {datetime.fromtimestamp(bidding_start)})")
                return 0
            elif current_time <= bidding_end:
                print(f"[NegotiationAgent] State: Bidding Phase (Ends at {datetime.fromtimestamp(bidding_end)})")
                return 1
            elif current_time <= reveal_end:
                print(f"[NegotiationAgent] State: Reveal Phase (Ends at {datetime.fromtimestamp(reveal_end)})")
                return 2
            else: # current_time > reveal_end
                print(f"[NegotiationAgent] State: Post-Reveal / Closing Pending (Ended at {datetime.fromtimestamp(reveal_end)})")
                return 3


        async def run(self):
            print("[NegotiationAgent] Behaviour loop started. Waiting for data...")
            await asyncio.sleep(5) # Initial wait before checking messages

            try:
                # Check auction status periodically regardless of messages
                bidding_start, bidding_end, reveal_end = await self.get_auction_timings()
                current_state = await self.current_auction_state(bidding_start, bidding_end, reveal_end)

                # --- Automatic Closing Logic ---
                if current_state == 3: # If auction is past reveal end, try to close it
                    print("[NegotiationAgent] Auction period ended, attempting to close...")
                    await self.close()
                    # After closing, timings should reset (bidding_start becomes 0),
                    # so the state will become -1 in the next loop iteration.
                    await asyncio.sleep(10) # Wait a bit after closing before next loop
                    return # End current run cycle after closing attempt

                # --- Receive Message and React ---
                msg = await self.receive(timeout=15) # Shorter timeout to allow periodic checks

                if msg:
                    print(f"[NegotiationAgent] Received message from {msg.sender}")
                    data = json.loads(msg.body)
                    house_data = data.get("house") # Example: {"current_production": 1.5, "current_demand": 0.8}
                    prediction_data = data.get("prediction") # Example: {"predicted_demand": 0.9, "predicted_production": 1.2}
                    demand_response_data = data.get("demandresponse") # Example: {"market_value": 0.15} # Price per kWh in ETH? Assume yes.
                    gui_data = data.get("gui") # Example: {"strategy": "aggressive"}

                    if not all([house_data, prediction_data, demand_response_data, gui_data]):
                        print(f"[NegotiationAgent] Missing data fields in received message: {data}")
                    else:
                        print("[NegotiationAgent] Received complete data set.")

                        # Use 'get' with defaults for safety
                        current_prod = house_data.get("current_production", 0)
                        current_demand = house_data.get("current_demand", 0)
                        market_price_eth_per_kwh = demand_response_data.get("market_value", 0.1) # Default market price?
                        strategy = gui_data.get("strategy", "neutral") # Default strategy
                
                # --- ROBUST CHECK FOR REQUIRED DATA ---
                        # Check if the core dictionaries exist and are dictionaries
                        if not isinstance(house_data, dict):
                            print(f"[N] Missing or invalid 'house' data in message.")
                            return # Skip cycle if essential data is missing/wrong type
                        if not isinstance(demand_response_data, dict):
                            print(f"[N] Missing or invalid 'demandresponse' data in message.")
                            return
                        if not isinstance(gui_data, dict):
                             print(f"[N] Missing or invalid 'gui' data in message.")
                             return
                        # Check for specific required keys WITHIN the dictionaries
                        if not all(k in house_data for k in ["current_production", "current_demand"]):
                            print(f"[N] Missing required keys in 'house' data.")
                            return
                        if "market_value" not in demand_response_data:
                             print(f"[N] Missing required 'market_value' in 'demandresponse' data.")
                             return
                        if "strategy" not in gui_data:
                              print(f"[N] Missing required 'strategy' in 'gui' data.")
                              return
                        # --- END ROBUST CHECK ---

                    # If checks pass, we can safely access the data
                        current_prod = house_data["current_production"]
                        current_demand = house_data["current_demand"]
                        market_price_eth_per_kwh = demand_response_data["market_value"]
                        strategy = gui_data["strategy"]
                        energy_delta_kwh = current_prod - current_demand
                        print(f"[NegotiationAgent] Calculated Energy Delta: {energy_delta_kwh:.2f} kWh")

                        # Decide whether to Buy or Sell based on delta
                        if energy_delta_kwh < -0.1: # Need to buy (added small threshold)
                            print("[NegotiationAgent] Energy deficit detected. Looking to buy.")
                            amount_to_buy_kwh = abs(energy_delta_kwh) # Try to buy the deficit

                            if current_state == 1: # Only bid if currently in bidding phase
                                print("[NegotiationAgent] In bidding phase. Calculating bid...")
                                bid_price_eth_per_kwh = market_price_eth_per_kwh
                                if strategy == "aggressive":
                                    bid_price_eth_per_kwh *= 1.05 # Bid 5% above market
                                elif strategy == "conservative":
                                    bid_price_eth_per_kwh *= 0.90 # Bid 10% below market
                                # Neutral strategy bids at market price

                                # Convert total price to Wei for the bid amount AND the value field
                                # NOTE: Vickrey means you bid your TRUE valuation. The *value* sent might
                                # just be a deposit, or it could be the max you're willing to pay.
                                # Assuming for Vickrey, you bid your true value per kWh, and send that amount
                                # as the deposit? Let's assume bid amount = max willing to pay total.
                                total_bid_value_eth = bid_price_eth_per_kwh * amount_to_buy_kwh # This seems conceptually wrong for Vickrey value field
                                # Re-think: The `value` sent with `bid()` is likely a deposit or the actual bid value if not sealed.
                                # For sealed Vickrey, the `value` might just need to cover the potential win amount (e.g., second price).
                                # Let's assume `value` sent must be >= bid amount revealed later. Simplest: send bid amount.
                                bid_amount_wei = self.web3.to_wei(bid_price_eth_per_kwh, "ether") # Bid is per unit? Contract dependent!
                                # *** CHECK YOUR CONTRACT: Does bid() take price per unit or total value? Does reveal() take price per unit or total? ***
                                # Assuming reveal() takes total value bid:
                                total_value_bid_wei = self.web3.to_wei(bid_price_eth_per_kwh * amount_to_buy_kwh, "ether")

                                await self.bid(total_value_bid_wei) # Pass total WEI value you are bidding

                            elif current_state == 2: # Reveal phase
                                print("[NegotiationAgent] In reveal phase. Attempting to reveal previous bid...")
                                # Need to ensure self.bid_amount was set correctly in the bidding phase run
                                if self.bid_amount > 0:
                                    await self.reveal()
                                else:
                                    print("[NegotiationAgent] No bid amount stored from bidding phase to reveal.")

                            else:
                                print(f"[NegotiationAgent] Not in Bidding or Reveal phase (State: {current_state}). Cannot act.")


                        elif energy_delta_kwh > 0.1: # Have surplus to sell (added threshold)
                            print("[NegotiationAgent] Energy surplus detected. Considering selling.")

                            if current_state == -1: # Only start auction if none is active
                                print("[NegotiationAgent] No active auction. Calculating sell amount...")
                                sell_fraction = 0.5 # Neutral default
                                if strategy == "aggressive":
                                    sell_fraction = 0.75
                                elif strategy == "conservative":
                                    sell_fraction = 0.25

                                amount_to_sell_kwh = energy_delta_kwh * sell_fraction
                                if amount_to_sell_kwh > 0.01: # Minimum amount to auction
                                     await self.start_auction(amount_to_sell_kwh)
                                else:
                                     print("[NegotiationAgent] Surplus too small to auction.")
                            else:
                                 print(f"[NegotiationAgent] Cannot start auction, one is already in progress (State: {current_state}).")

                        else: # Close to balanced
                             print("[NegotiationAgent] Energy nearly balanced. No buy/sell action needed.")

                else:
                    print("[NegotiationAgent] No message received in this cycle.")
                    # Agent can still perform actions based on time/state even without messages
                    if current_state == 2 and self.bid_amount > 0:
                         print("[NegotiationAgent] In reveal phase (no message). Attempting reveal.")
                         await self.reveal()
                
                await self.call_trade_summary()

            except json.JSONDecodeError:
                print(f"[NegotiationAgent] Error decoding JSON from message: {msg.body}")
            except AssertionError as ae:
                 print(f"[NegotiationAgent] Assertion Error: {ae}") # Catch web3 connection issues etc.
                 # Consider stopping or waiting before retry
                 await asyncio.sleep(30)
            except Exception as e:
                print(f"[NegotiationAgent] An error occurred in TradingBehaviour run: {e}")
                import traceback
                traceback.print_exc() # Print full traceback for debugging
                # Log error to DB?
                await asyncio.sleep(10) # Wait after error before next loop

            # Wait before the next loop iteration regardless of messages/actions
            await asyncio.sleep(5)


    async def setup(self):
        print("[NegotiationAgent] Started")
        # Add the trading behavior
        trading_b = self.TradingBehaviour()
        self.add_behaviour(trading_b)
        try:
            self.web.start(hostname="localhost", port="9095")
            print("[NegotiationAgent] Web server started.")
        except Exception as e:
             print(f"[NegotiationAgent] Failed to start web server: {e}")