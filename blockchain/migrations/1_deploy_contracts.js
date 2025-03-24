const EnergyVickreyAuction = artifacts.require("EnergyVickreyAuction");

module.exports = function (deployer) {
    const biddingTime = 300; // Example: 5 minutes (in seconds)
    const revealTime = 180;  // Example: 3 minutes (in seconds)
    
    deployer.deploy(EnergyVickreyAuction, biddingTime, revealTime);
};
