// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract ConsensusLedger {
    struct ConsensusRecord {
        bytes32 queryHash;
        bytes32 answerHash;
        bytes32 sageVote;
        bytes32 guardianVote;
        bytes32 empathVote;
        bytes32 oracleVote;
        bool consensusReached;
        uint256 timestamp;
        string status;
    }

    mapping(bytes32 => ConsensusRecord) public records;
    bytes32[] public recordIds;

    event ConsensusLogged(
        bytes32 indexed sessionId,
        bool consensusReached,
        string status,
        uint256 timestamp
    );

    function logConsensus(
        bytes32 _sessionId,
        bytes32 _queryHash,
        bytes32 _answerHash,
        bytes32 _sageVote,
        bytes32 _guardianVote,
        bytes32 _empathVote,
        bytes32 _oracleVote,
        bool _consensusReached,
        string memory _status
    ) public {
        records[_sessionId] = ConsensusRecord({
            queryHash: _queryHash,
            answerHash: _answerHash,
            sageVote: _sageVote,
            guardianVote: _guardianVote,
            empathVote: _empathVote,
            oracleVote: _oracleVote,
            consensusReached: _consensusReached,
            timestamp: block.timestamp,
            status: _status
        });

        recordIds.push(_sessionId);
        emit ConsensusLogged(_sessionId, _consensusReached, _status, block.timestamp);
    }

    function getRecord(bytes32 _sessionId) public view returns (ConsensusRecord memory) {
        return records[_sessionId];
    }

    function getTotalRecords() public view returns (uint256) {
        return recordIds.length;
    }
}
