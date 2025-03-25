const fs = require('fs');
const path = require('path');
const EnergyVickreyAuction = artifacts.require("EnergyVickreyAuction");

module.exports = async function (deployer) {
    const biddingTime = 15;  // Time in seconds (30 seconds in this case)
    const revealTime = 5;   // Time in seconds (20 seconds in this case)
    const nextRoundDelay = 2; // Time in seconds for the next auction round delay

    deployer.deploy(EnergyVickreyAuction, biddingTime, revealTime).then(async (instance) => {
        const contractAddress = instance.address;
        console.log("Contract deployed to:", contractAddress);

        // Update the .env file with the new contract details
        const envFilePath = path.join(__dirname, '..', '.env');

        // Load existing .env content if available
        let envContent = '';
        if (fs.existsSync(envFilePath)) {
            envContent = fs.readFileSync(envFilePath, 'utf8');
        }

        // Create or update the .env content with new variables
        const newEnvContent = [
            `CONTRACT_ADDRESS=${contractAddress}`,
            `BIDDING_TIME=${biddingTime}`,
            `REVEAL_TIME=${revealTime}`,
            `NEXT_ROUND_DELAY=${nextRoundDelay}`,
        ].join('\n');

        // Overwrite the .env file with the updated values
        fs.writeFileSync(envFilePath, newEnvContent, 'utf8');
        console.log(`.env file updated with CONTRACT_ADDRESS, BIDDING_TIME, REVEAL_TIME, and NEXT_ROUND_DELAY.`);
    });
};
