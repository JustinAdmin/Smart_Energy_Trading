const fs = require('fs');
const path = require('path');
const EnergyVickreyAuction = artifacts.require("EnergyVickreyAuction");

module.exports = async function (deployer) {
    const biddingTime = 90;  // Time in seconds (90 seconds in this case)
    const revealTime = 40;   // Time in seconds (30 seconds in this case)

    deployer.deploy(EnergyVickreyAuction, biddingTime, revealTime).then(async (instance) => {
        const contractAddress = instance.address;
        console.log("Contract deployed to:", contractAddress);

        // Update the .env file with the new contract address
        const envFilePath = path.join(__dirname, '..', '.env');
        
        // Create the new .env content with CONTRACT_ADDRESS
        const newEnvContent = `CONTRACT_ADDRESS=${contractAddress}\n`;

        // Overwrite the .env file with the new contract address
        fs.writeFileSync(envFilePath, newEnvContent, 'utf8');
        console.log(`.env file updated with CONTRACT_ADDRESS=${contractAddress}`);
    });
};
