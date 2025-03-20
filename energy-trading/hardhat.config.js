/** @type import('hardhat/config').HardhatUserConfig */
require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: "0.8.20",
  networks: {
    localhost: { 
      url: "http://localhost:8545", 
      accounts: [process.env.PRIVATE_KEY],
    },
  },
};

//module.exports = {
//  solidity: "0.8.20",
//  networks: {
//    sepolia: {
//      url: `https://eth-sepolia.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY}`,
//      accounts: [process.env.PRIVATE_KEY],
//    },
//  },
//};
