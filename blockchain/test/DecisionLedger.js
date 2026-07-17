const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("DecisionLedger", function () {
  async function deployLedger() {
    const [owner, other] = await ethers.getSigners();
    const factory = await ethers.getContractFactory("DecisionLedger");
    const ledger = await factory.deploy();
    await ledger.waitForDeployment();
    return { ledger, owner, other };
  }

  it("allows only the owner to write a decision", async function () {
    const { ledger, other } = await deployLedger();
    await expect(
      ledger.connect(other).logDecision(ethers.id("record-1"), ethers.id("decision-1"), "APPROVED")
    ).to.be.revertedWith("DecisionLedger: caller is not owner");
  });

  it("stores the writer and prevents record overwrite", async function () {
    const { ledger, owner } = await deployLedger();
    const recordId = ethers.id("record-1");
    const decisionHash = ethers.id("decision-1");

    await ledger.logDecision(recordId, decisionHash, "BLOCKED");
    const record = await ledger.getRecord(recordId);

    expect(record.decisionHash).to.equal(decisionHash);
    expect(record.status).to.equal("BLOCKED");
    expect(record.writer).to.equal(owner.address);
    expect(record.exists).to.equal(true);
    expect(await ledger.getTotalRecords()).to.equal(1n);

    await expect(
      ledger.logDecision(recordId, ethers.id("decision-2"), "APPROVED")
    ).to.be.revertedWith("DecisionLedger: record already exists");
  });
});
