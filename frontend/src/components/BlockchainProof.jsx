import React from 'react'

export default function BlockchainProof({ txHash }) {
  if (!txHash || !txHash.startsWith('0x')) return null
  return (
    <div style={{ fontSize: '12px', marginTop: '8px' }}>
      <a 
        href={`https://mumbai.polygonscan.com/tx/${txHash}`} 
        target="_blank" 
        rel="noreferrer"
        style={{ color: '#60a5fa' }}
      >
        View on Polygon Mumbai
      </a>
    </div>
  )
}
