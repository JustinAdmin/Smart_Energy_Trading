const EnergyVickreyAuction = artifacts.require("EnergyVickreyAuction");

module.exports = function (deployer) {
    const biddingTime = 600; // Example: 10 minutes (in seconds)
    const revealTime = 300;  // Example: 5 minutes (in seconds)
    
    deployer.deploy(EnergyVickreyAuction, biddingTime, revealTime);
};
