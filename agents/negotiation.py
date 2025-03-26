from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from web3 import Web3
import json
import os
from dotenv import load_dotenv  # pip install python-dotenv
import asyncio
from datetime import datetime

# Negotiation Agent: Facilitates peer-to-peer energy trading
class NegotiationAgent(Agent):
    class TradingBehaviour(CyclicBehaviour):
        async def on_start(self):
            # Connect to local blockchain (Ganache)
            self.web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
            assert self.web3.is_connected(), "Failed to connect to the blockchain"

            # Load environment variables from the .env file
            load_dotenv()

            # Load contract address dynamically
            project_dir = os.path.dirname(os.path.dirname(__file__))  # Correct path logic
            env_path = os.path.join(project_dir, "blockchain", ".env")
            load_dotenv(env_path)  # Ensure .env is loaded from the correct location

            contract_address = os.getenv("CONTRACT_ADDRESS")
            assert contract_address, "Contract address not found in .env file."

            # Ensure the contract is deployed
            code = self.web3.eth.get_code(contract_address)
            assert code != b'0x', "Contract address is invalid or the contract is not deployed."

            # Load the contract ABI dynamically
            contract_path = os.path.join(project_dir, "blockchain", "build", "contracts", "EnergyVickreyAuction.json")

            with open(contract_path, "r") as abi_file:
                contract_data = json.load(abi_file)

            # Validate ABI structure
            if 'abi' not in contract_data or not isinstance(contract_data['abi'], list):
                raise ValueError("ABI is missing or invalid in the contract JSON file.")

            contract_abi = contract_data['abi']
            print(f"[NegotiationAgent] Ganache connected: {self.web3.is_connected()}")

            # Initialize the contract
            self.auction_contract = self.web3.eth.contract(address=contract_address, abi=contract_abi)

            # Define bidder accounts (from Ganache)
            self.accounts = self.web3.eth.accounts
            self.account = self.accounts[0]

            self.bid_amount = 0
            self.nonce = "mainhouse"
        
        def set_bid_amount(self, price):
            self.bid_amount = price
        
        async def create_sealed_bid(self, value, nonce):
            # Change to match contract's keccak256(abi.encodePacked()) format
            encoded = Web3.solidity_keccak(['uint256', 'string'], [value, nonce])
            return encoded
        
        async def get_auction_timings(self):
            bidding_start = self.auction_contract.functions.biddingStart().call()
            reveal_start = self.auction_contract.functions.biddingEnd().call()
            reveal_end = self.auction_contract.functions.revealEnd().call()
            return bidding_start, reveal_start, reveal_end
        
        async def wait_until(end_datetime):
    
            end_datetime = datetime.fromtimestamp(end_datetime)
            
            diff = (end_datetime - datetime.now()).total_seconds()
            while diff > 1:
                diff = (end_datetime - datetime.now()).total_seconds()
                print(f'[NegotiationAgent] Time Until End of Bid: {diff}')    # In case end_datetime was in past to begin with
                asyncio.sleep(diff/2)
            asyncio.sleep(2)
            return
        
        async def start_auction(self, energy_amount=5):
            # Wait for the last auction to end and then start a new one
            auction_started = self.auction_contract.functions.biddingStart().call()
            while auction_started != 0:
                auction_started = self.auction_contract.functions.biddingStart().call()
            
            # Once auction_started is 0 start the auction
            bidding_duration = int(os.getenv("BIDDING_TIME")) 
            reveal_duration = int(os.getenv("REVEAL_TIME"))  
            tx = self.auction_contract.functions.startAuction(energy_amount).transact({
                'from': self.account,
                'gas': 3000000,
                'gasPrice': self.web3.to_wei('20', 'gwei')
            })
            self.web3.eth.wait_for_transaction_receipt(tx)
            print(f"[NegotiationAgent] Auction started with bidding duration {bidding_duration} and reveal duration {reveal_duration}!")
        
        async def bid(self, price=5):
            self.set_bid_amount(price)
            try:
                sealed_bid = await self.create_sealed_bid(self.bid_amount, self.nonce)
                tx = self.auction_contract.functions.bid(sealed_bid).transact({
                    "from": self.account,
                    "value": self.bid_amount,
                    "gas": 3000000
                })
                self.web3.eth.wait_for_transaction_receipt(tx)
                print(f"[NegotiationAgent] Bid placed by {self.account}")
            except Exception as e:
                print(f"[NegotiationAgent] Failed to place bid for {self.account}: {e}")
        
        async def reveal(self):
            try:
                tx = self.auction_contract.functions.reveal(self.bid_amount, self.nonce).transact({
                    'from': self.account,
                    "gas": 3000000
                })
                self.web3.eth.wait_for_transaction_receipt(tx)
                print(f"[NegotiationAgent] Bid revealed by {self.account}!")
            except Exception as e:
                print(f"[NegotiationAgent] Failed to reveal bid for {self.account}: {e}")

            print("[NegotiationAgent] Bid revealed!")

        async def close(self):
            # Step 6: Close the auction
            print("[NegotiationAgent] Close auction...")
            try:
                tx = self.auction_contract.functions.closeAuction().transact({
                    "from": self.account,
                    "gas": 3000000
                })
                self.web3.eth.wait_for_transaction_receipt(tx)
                winner = self.auction_contract.functions.highestBidder().call()
                final_price_wei = self.auction_contract.functions.secondHighestBid().call()
                final_price_eth = self.web3.from_wei(final_price_wei, "ether")
                energy = self.auction_contract.functions.energyAmount().call()
                print(f"[NegotiationAgent] Auction Winner: {winner} \n[NegotiationAgent] Energy: {energy} kWh \n[NegotiationAgent] Price: {final_price_eth} ETH")
            except Exception as e:
                print(f"[NegotiationAgent] Failed to close auction: {e}")

        async def run(self):
            print("[NegotiationAgent] Waiting for surplus energy data...")
            await asyncio.sleep(5)
            msg = await self.receive(timeout=30)
            if msg:
                try:
                    data = json.loads(msg.body)
                    house_data = data.get("house") # current_production and current_demand
                    prediction_data = data.get("prediction") # predicted production and demand?
                    demand_response_data = data.get("demandresponse") # market_value
                    gui_data = data.get("gui") # strategy

                    if house_data is None or prediction_data is None or demand_response_data is None or gui_data is None:
                        print(f"[NegotiationAgent] Missing data: {data}")
                    
                    else:

                        energy_delta = house_data.get("current_production") - house_data.get("current_demand")
                        
                        if energy_delta < 0:
                            # Get the timing variables
                            bidding_start, bidding_end, reveal_end = await self.get_auction_timings()
                            while bidding_start < datetime.now().timestamp():
                                # Get the timing variables
                                bidding_start, bidding_end, reveal_end = await self.get_auction_timings()

                            # We are in an energy deficit and need to purchase energy
                            strategy = gui_data.get("strategy")
                            market = demand_response_data.get("market_value")

                            # Wait for next round of bidding
                            await self.wait_until(bidding_start)

                            match strategy:
                                case "aggressive":
                                    # Buy at 102% market
                                    await self.bid(market * 1.02)
                                case "neutral":
                                    # Buy at 95% market
                                    await self.bid(market * 0.95)
                                case "conservative":
                                    # Buy at 85% market
                                    await self.bid(market * 0.85)
                            
                            await self.wait_until(bidding_end)

                            await self.reveal()
                        else:
                            # We are energy neutral or in a surplus and want to store/sell
                            
                            match strategy:
                                case "aggressive":
                                    # 25 conserve / 75 sell
                                    await self.start_auction(energy_delta * 0.75)
                                case "neutral":
                                    # 50 conserve / 50 sell
                                    await self.start_auction(energy_delta * 0.75)
                                case "conservative":
                                    # 75 conserve / 25 sell
                                    await self.start_auction(energy_delta * 0.75)
                            
                            # Get the timing variables
                            bidding_start, bidding_end, reveal_end = await self.get_auction_timings()

                            await self.wait_until(reveal_end)

                            await self.close()
                    
                except Exception as e:
                    print(f"[NegotiationAgent] Error: {e}")
                    print(f"[NegotiationAgent] {msg}")

    async def setup(self):
        print("[NegotiationAgent] Started")
        self.add_behaviour(self.TradingBehaviour())
        self.web.start(hostname="localhost", port="9095")
