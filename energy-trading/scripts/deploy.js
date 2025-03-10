const hre = require("hardhat");

async function main() {
  const EnergyTrading = await hre.ethers.getContractFactory("EnergyTrading"); // Ensure contract name matches
  const energyTrading = await EnergyTrading.deploy(); // Deploy contract

  await energyTrading.waitForDeployment(); // Use waitForDeployment() instead of deployed()

  console.log(`EnergyTrading deployed to: ${await energyTrading.getAddress()}`); //getAddress() replaces .address
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
