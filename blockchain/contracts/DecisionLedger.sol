// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract DecisionLedger {
    struct DecisionRecord {
        bytes32 decisionHash;
        string status;
        uint256 timestamp;
        address writer;
        bool exists;
    }

    address public owner;
    mapping(bytes32 => DecisionRecord) public records;
    bytes32[] public recordIds;

    event DecisionLogged(
        bytes32 indexed recordId,
        bytes32 indexed decisionHash,
        string status,
        address indexed writer,
        uint256 timestamp
    );
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "DecisionLedger: caller is not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "DecisionLedger: zero owner");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    function logDecision(
        bytes32 recordId,
        bytes32 decisionHash,
        string calldata status
    ) external onlyOwner {
        require(!records[recordId].exists, "DecisionLedger: record already exists");
        records[recordId] = DecisionRecord({
            decisionHash: decisionHash,
            status: status,
            timestamp: block.timestamp,
            writer: msg.sender,
            exists: true
        });
        recordIds.push(recordId);
        emit DecisionLogged(recordId, decisionHash, status, msg.sender, block.timestamp);
    }

    function getRecord(bytes32 recordId) external view returns (DecisionRecord memory) {
        require(records[recordId].exists, "DecisionLedger: unknown record");
        return records[recordId];
    }

    function getTotalRecords() external view returns (uint256) {
        return recordIds.length;
    }
}
