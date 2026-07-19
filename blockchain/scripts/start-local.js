const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  const DecisionLedger = await hre.ethers.getContractFactory("DecisionLedger");
  const ledger = await DecisionLedger.deploy();
  await ledger.waitForDeployment();

  const address = await ledger.getAddress();
  console.log("DecisionLedger deployed to:", address);
  console.log("\nAdd this to your .env:");
  console.log(`BLOCKCHAIN_CONTRACT_ADDRESS=${address}`);
  console.log("BLOCKCHAIN_RPC_URL=http://host.docker.internal:8545");
  console.log("BLOCKCHAIN_NETWORK=local");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
