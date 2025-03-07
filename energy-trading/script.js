const { ethers } = require("ethers");
require("dotenv").config();

// Load environment variables
const ALCHEMY_API_KEY = process.env.ALCHEMY_API_KEY;
const NETWORK_URL = `https://eth-sepolia.g.alchemy.com/v2/${ALCHEMY_API_KEY}`;
const PRIVATE_KEY = process.env.PRIVATE_KEY;

if (!ALCHEMY_API_KEY || !PRIVATE_KEY) {
  console.error("❌ Missing API Key or Private Key in .env file!");
  process.exit(1);
}

// Connect to the Ethereum provider
const provider = new ethers.JsonRpcProvider(NETWORK_URL);
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);


async function fetchBlock(blockNumber) {
  try {
    const blockNumber = "latest";
    const block = await provider.getBlock(blockNumber);
    console.log("✅ Block Data:", block);
  } catch (error) {
    console.error("❌ Error fetching block:", error);
  }
}

// Fetch a specific block
fetchBlock(15221026);
