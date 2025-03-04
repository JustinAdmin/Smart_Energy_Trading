const hre = require("hardhat");

async function main() {
  const EnergyTrading = await hre.ethers.getContractFactory("EnergyTrading"); // ✅ Ensure contract name matches
  const energyTrading = await EnergyTrading.deploy();

  await energyTrading.deployed();
  console.log(`EnergyTrading deployed to: ${energyTrading.address}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
