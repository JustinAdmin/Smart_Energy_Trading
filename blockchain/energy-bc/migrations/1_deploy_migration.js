const EnergyTrading = artifacts.require("EnergyTrading");//
module.exports = function(deployer) {
  // deployment steps
  deployer.deploy(EnergyTrading);
};

//const BlindEnergyTrading = artifacts.require("BlindEnergyTrading");
//
//module.exports = function (deployer, network, accounts) {
//  const demandResponseAgent = accounts[0]; // Example agent address
//  const auctionDuration = 1 * 60;     // 1 min auction duration (adjust as needed)
//
//  deployer.deploy(BlindEnergyTrading, demandResponseAgent, auctionDuration);
//};


// accounts[0] is the first account in the list of accounts provided by the Ethereum client gandache-cli
// accounts[1] is the second account that an agent can use 
// accounts[2] is the third account that an agent can use
// accounts[3] is the fourth account that an agent can use
// demandResponseAgent is the address of the agent that will be responsible for demand response
// auctionDuration is the duration of the auction in seconds
// The BlindEnergyTrading contract is deployed with the demandResponseAgent and auctionDuration parameters