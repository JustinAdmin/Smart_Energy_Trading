# Using Winget to manage package installations:

    # Step 1: Navigate to your project directory where you want to install Hardhat:
    cd \energy-trading  # Replace with your actual project directory path

    # Step 2: Download and install FNM (Fast Node Manager) using Winget:
    # This allows for quick management of different Node.js versions.
    winget install Schniz.fnm

    # Step 3: Install Node.js version 18 using FNM:
    # This ensures you're using a compatible Node.js version (18.x) for Hardhat.
    fnm install 18

    # Step 4: Verify the installed version of Node.js:
    # This command checks if Node.js 18 is successfully installed.
    node -v # Should print "v18.x.x".

    # Step 5: Verify the npm (Node Package Manager) version:
    # This checks the installed version of npm to ensure compatibility.
    npm -v # Should print an npm version like "10.x.x".

# If Winget and FNM don't work or if you're having trouble, you can use NVM (Node Version Manager):
# Download and install NVM for Windows from the following link:
# https://github.com/coreybutler/nvm-windows/releases

# Step 1: Download NVM for Windows and install it as instructed.

# Step 2: After installing NVM, open a new PowerShell window and use the following command to install Node.js version 18:
cd \energy-trading  # Make sure you're in your project directory
nvm install 18

# Step 3: Set Node.js version 18 as the active version:
nvm use 18

# Install Hardhat (Ethereum Development Framework):

        # Step 1: Install Hardhat as a development dependency:
        # This will install Hardhat in your project directory.
    npm install --save-dev hardhat

        # Step 2: Install Hardhat Toolbox:
        # The Hardhat Toolbox includes useful plugins for working with smart contracts, deployment, and more.
    npm install --save-dev @nomicfoundation/hardhat-toolbox

        # Step 3: Install Hardhat Ethers plugin and Ethers.js:
        # This will allow you to interact with the Ethereum network and deploy contracts with Ethers.js.
    npm install --save-dev @nomicfoundation/hardhat-ethers ethers

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

        # Step 1: Run the deployment script:
        # This deploys the smart contract to the local Ethereum blockchain (running on localhost).
    npx hardhat run scripts/deploy.js --network localhost
