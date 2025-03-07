## docker containter help:(optional)

docker build -t energy-trading .
docker run -it --rm -v ${PWD}:/app -w /app energy-trading /bin/bash

# Using Winget to manage package installations:

    cd \energy-trading  # Replace with your actual project directory path

    # This allows for quick management of different Node.js versions.
    winget install Schniz.fnm # run in admin power PowerShell
    fnm install 18
    node -v # Should print "v18.x.x".
    npm -v # Should print an npm version like "10.x.x".
    npm install dotenv --save
    
# If Winget and FNM don't work or if you're having trouble, you can use NVM (Node Version Manager):
# Download and install NVM for Windows from the following link:
# https://github.com/coreybutler/nvm-windows/releases

# Step 1: Download NVM for Windows and install it as instructed.

# Step 2: After installing NVM, open a new PowerShell window and use the following command to install Node.js version 18:
cd \energy-trading  # Make sure you're in your project directory
nvm install 18
fnm env --use-on-cd --shell powershell | Out-String | Invoke-Expression
    # Step 3: Set Node.js version 18 as the active version:
    #nvm use 18
fnm use 18

# Install Hardhat (Ethereum Development Framework) MUST BE CMD terminal:
Open up a cmd terminal in VScode in the energy-trading folder first
        # Step 1: Install Hardhat as a development dependency: This will install Hardhat in your project directory.
    npm install --save-dev hardhat
            # dotenv should already be install but you may run this below to check the packages are already up-to-date
            #npm install dotenv --save
        # Step 2: Install Hardhat Toolbox:
        #npm install --save-dev @nomicfoundation/hardhat-toolbox

        # Step 3: Install Hardhat Ethers plugin and Ethers.js:
        # This will allow you to interact with the Ethereum network and deploy contracts with Ethers.js.
        #npm install --save-dev @nomicfoundation/hardhat-ethers
        
        # add hardhat to env path
    $env:Path += ";$PWD\node_modules\.bin"

        #run this command to check the scope of hardhat install location
    npm list hardhat
# Initialize the Hardhat project:

        # Step 1: Create a Hardhat project by running:
        # This will guide you through setting up a Hardhat project in the correct directory.
    npx hardhat
    
    # Once prompted, press TAB 3 times to select the "Create an empty hardhat.config.js" option, then press Enter.

# Compile your smart contracts:

        # Step 1: Compile your smart contracts:
        # This compiles the contracts in your Hardhat project, ensuring they're ready for deployment.
    npx hardhat compile

# Start a local Ethereum blockchain node:

        # Step 1: Start a local Ethereum node for testing:
        # This will start a local Ethereum blockchain where you can deploy your smart contracts and test them.
    npx hardhat node

# Deploy your smart contracts:

#run this code to check if this code is connected to the blockchain.
    
    node script.js

#lastly, if the solidity EnergyTrading.sol contract is set up the way its intended you can deploy the contract on the blockchain now.

npx hardhat run scripts/deploy.js --network sepolia

# should return 
    #EnergyTrading deployed to: 0xe37baD0ebecffBecaB13A53DEb58b051ca4dFAd3

