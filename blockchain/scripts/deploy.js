const hre = require("hardhat");

async function main() {
  const ConsensusLedger = await hre.ethers.getContractFactory("ConsensusLedger");
  const ledger = await ConsensusLedger.deploy();
  await ledger.waitForDeployment();

  console.log("ConsensusLedger deployed to:", await ledger.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
