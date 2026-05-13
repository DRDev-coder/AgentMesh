import React from 'react'

export default function ConsensusBadge({ status, txHash }) {
  return (
    <div>
      {status === 'CONSENSUS_REACHED' && <span>Verified</span>}
      {txHash && <a href={`https://mumbai.polygonscan.com/tx/${txHash}`}>Proof</a>}
    </div>
  )
}
