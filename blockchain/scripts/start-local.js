const hre = require("hardhat");

async function main() {
  // Start local Hardhat node with 10,000 ETH for testing
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  const ConsensusLedger = await hre.ethers.getContractFactory("ConsensusLedger");
  const ledger = await ConsensusLedger.deploy();
  await ledger.waitForDeployment();

  const address = await ledger.getAddress();
  console.log("ConsensusLedger deployed to:", address);
  console.log("\nAdd this to your .env:");
  console.log(`CONTRACT_ADDRESS=${address}`);
  console.log(`ALCHEMY_URL=http://127.0.0.1:8545`);
  console.log("\nLocal node is running. Press Ctrl+C to stop.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
