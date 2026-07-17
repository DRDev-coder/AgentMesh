const hre = require("hardhat");

async function main() {
  const DecisionLedger = await hre.ethers.getContractFactory("DecisionLedger");
  const ledger = await DecisionLedger.deploy();
  await ledger.waitForDeployment();

  console.log("DecisionLedger deployed to:", await ledger.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
