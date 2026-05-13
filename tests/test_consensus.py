import pytest
import sys
sys.path.insert(0, '/app')
from consensus.pbft_consensus import ConsensusEngine, AgentVote


def test_consensus_reached():
    engine = ConsensusEngine(total_agents=4, fault_tolerance=1)
    votes = [
        AgentVote("sage", "answer A", 90, "AGREE", []),
        AgentVote("guardian", "answer A", 100, "AGREE", []),
        AgentVote("empath", "answer A", 80, "AGREE", []),
        AgentVote("oracle", "answer A", 95, "AGREE", [])
    ]
    result = engine.reach_consensus(votes, [])
    assert result["status"] == "CONSENSUS_REACHED"
    assert result["final_answer"] == "answer A"


def test_guardian_critical_blocks():
    engine = ConsensusEngine(total_agents=4, fault_tolerance=1)
    votes = [
        AgentVote("sage", "answer A", 90, "AGREE", []),
        AgentVote("guardian", "answer A", 0, "AGREE", []),
        AgentVote("empath", "answer A", 80, "AGREE", []),
        AgentVote("oracle", "answer A", 95, "AGREE", [])
    ]
    result = engine.reach_consensus(votes, ["CRITICAL"])
    assert result["status"] == "BLOCKED"
    assert result["escalate"] is True


def test_hallucination_blocked():
    engine = ConsensusEngine(total_agents=4, fault_tolerance=1)
    votes = [
        AgentVote("sage", "answer A", 90, "AGREE", []),
        AgentVote("guardian", "answer A", 100, "AGREE", []),
        AgentVote("empath", "answer A", 80, "DISAGREE", []),
        AgentVote("oracle", "answer B", 0, "DISAGREE", ["HALLUCINATION"])
    ]
    result = engine.reach_consensus(votes, [])
    assert result["status"] == "HALLUCINATION_BLOCKED"
    assert result["escalate"] is True


def test_no_consensus():
    engine = ConsensusEngine(total_agents=4, fault_tolerance=1)
    votes = [
        AgentVote("sage", "answer A", 90, "AGREE", []),
        AgentVote("guardian", "answer B", 100, "DISAGREE", []),
        AgentVote("empath", "answer C", 80, "DISAGREE", []),
        AgentVote("oracle", "answer D", 95, "DISAGREE", [])
    ]
    result = engine.reach_consensus(votes, [])
    assert result["status"] == "NO_CONSENSUS"
    assert result["escalate"] is True
