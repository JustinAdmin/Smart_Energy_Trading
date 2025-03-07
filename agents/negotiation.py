from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
from web3 import Web3

# Connect to Ethereum Sepolia Testnet Blockchain via Alchemy
ALCHEMY_URL = "https://eth-sepolia.g.alchemy.com/v2/ALCHEMY_API_KEY" # Use .env for security
PRIVATE_KEY = "PRIVATE_KEY"  # Use .env for security
CONTRACT_ADDRESS = "DEPLOYED_CONTRACT_ADDRESS"# Use .env for security

# Connect to Ethereum Network
web3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))
account = web3.eth.account.from_key(PRIVATE_KEY)

# Load Contract ABI
import json
with open("artifacts/contracts/EnergyTrading.sol/EnergyTrading.json") as f:
    contract_json = json.load(f)
    contract_abi = contract_json["abi"]

contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)


# Negotiation Agent: Facilitates peer-to-peer energy trading
class NegotiationAgent(Agent):
    class TradingBehaviour(CyclicBehaviour):
        async def run(self):
            print("[NegotiationAgent] Waiting for surplus energy data...")
            msg = await self.receive(timeout=5)
            if msg:
                try:
                    data = json.loads(msg.body).get("house")
                    print(f"[NegotiationAgent] Received data: {data}")

                    # If there is surplus energy, create a trade on the blockchain
                    if data.get("surplus_energy") > 0:
                        trade_amount = min(data["surplus_energy"], 2.0)  # Trade rule
                        trade_price = trade_amount * 0.5  # Example pricing rule (0.5 CAD per kWh)

                        # Execute blockchain transaction
                        tx_hash = create_trade(trade_amount, trade_price)

                        # Send trade confirmation to Facilitating Agent
                        response = Message(to="facilitating@localhost")
                        response.body = json.dumps({"traded_energy": trade_amount, "tx_hash": tx_hash})

                        await self.send(response)
                        print(f"[NegotiationAgent] Sent trade decision to FacilitatingAgent: {response.body}")

                except json.JSONDecodeError:
                    print(f"[NegotiationAgent] Invalid message format: {msg.body}")

    async def setup(self):
        print("[NegotiationAgent] Started")
        self.add_behaviour(self.TradingBehaviour())
        self.web.start(hostname="localhost", port="9095")


# Function to Create a Trade on the Blockchain
def create_trade(energy_amount, price):
    tx = contract.functions.createTrade(int(energy_amount), int(price)).build_transaction({
        "from": account.address,
        "gas": 2000000,
        "gasPrice": web3.to_wei("10", "gwei"),
        "nonce": web3.eth.get_transaction_count(account.address),
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return web3.to_hex(tx_hash)
