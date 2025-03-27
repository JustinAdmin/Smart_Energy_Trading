const fs = require('fs');
const path = require('path');
const EnergyVickreyAuction = artifacts.require("EnergyVickreyAuction");

module.exports = async function (deployer, network, accounts) {
    // --- Configuration ---
    const biddingTime = 20;  // Time in seconds
    const revealTime = 10;   // Time in seconds
    const nextRoundDelay = 2; // Time in seconds
    //const deployGas = 6000000; // Gas limit for deployment

    console.log(`Deploying EnergyVickreyAuction with biddingTime=${biddingTime}, revealTime=${revealTime}...`);

    try {
        // --- Deployment ---
        await deployer.deploy(
            EnergyVickreyAuction,
            biddingTime,
            revealTime,
            { from: accounts[0] }
        );
        const instance = await EnergyVickreyAuction.deployed();
        const contractAddress = instance.address;
        console.log(`✅ EnergyVickreyAuction deployed successfully at: ${contractAddress}`);

        // --- Overwrite .env file ---
        // Calculate path ONCE
        const envFilePath = path.join(__dirname, '..', '.env'); // Assumes .env is in blockchain/

        // Define the exact content for the new .env file
        const newEnvContent = [
            `CONTRACT_ADDRESS=${contractAddress}`,
            `BIDDING_TIME=${biddingTime}`,
            `REVEAL_TIME=${revealTime}`,
            `NEXT_ROUND_DELAY=${nextRoundDelay}`,
        ].join('\n');

        // --- Debugging and Writing Section ---
        // ** Removed second declaration of envFilePath **
        console.log(`DEBUG: __dirname = ${__dirname}`);
        console.log(`DEBUG: Calculated .env path = ${envFilePath}`);
        console.log(`DEBUG: Checking if path exists before write: ${fs.existsSync(envFilePath)}`);
        console.log(`DEBUG: Content to be written:\n${newEnvContent}`);

        try {
            // Attempt to write the file ONCE, inside the try block
            fs.writeFileSync(envFilePath, newEnvContent + '\n', 'utf8');
            console.log(`✅ SUCCESS: .env file write successful at ${envFilePath}`);
        } catch (writeError) {
            console.error(`❌ ERROR writing to .env file at ${envFilePath}:`, writeError);
            // Optional: Re-throw error if you want migration to fail hard on write error
            // throw writeError;
        }
        // ** Removed the second, redundant writeFileSync call **
        // ** Removed the second console.log for overwrite success **

    } catch (error) {
        // This catches errors from deployment *or* if the writeError is re-thrown above
        console.error(`❌ Deployment or .env operation failed: ${error}`);
    }
};