import React from 'react';

export default function ConfidenceBadge({ score, className = '' }) {
  const numScore = parseFloat(score) || 0;
  let scoreColor = 'text-red-400 bg-red-500/10 border-red-500/30';
  if (numScore >= 75) {
    scoreColor = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
  } else if (numScore >= 50) {
    scoreColor = 'text-amber-400 bg-amber-500/10 border-amber-500/30';
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-bold border ${scoreColor} ${className}`}>
      {score != null ? `${score}%` : 'N/A'}
    </span>
  );
}
