import { useState } from 'react';
import type { Analysis } from '../api';
import { triggerAnalysis } from '../api';
import { HiOutlinePlay } from 'react-icons/hi2';

interface Props {
  analyses: Analysis[];
  selectedId: string;
  onSelect: (id: string) => void;
  onRunComplete: () => void;
}

function formatRunLabel(a: Analysis): string {
  const d = new Date(a.run_date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
  return `${d} — ${a.total_tickets} tickets`;
}

export default function RunSelector({ analyses, selectedId, onSelect, onRunComplete }: Props) {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');

  async function handleRun() {
    setRunning(true);
    setError('');
    try {
      await triggerAnalysis(24);
      onRunComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
      setTimeout(() => setError(''), 4000);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      {analyses.length > 0 && (
        <select
          value={selectedId}
          onChange={(e) => onSelect(e.target.value)}
          className="glass-card rounded-lg px-3 py-2 text-sm text-ws-text bg-transparent focus:outline-none focus:border-ws-green cursor-pointer min-w-[240px]"
        >
          {analyses.map((a) => (
            <option key={a._id} value={a._id} className="bg-[#111827] text-[#e5e7eb]">
              {formatRunLabel(a)}
            </option>
          ))}
        </select>
      )}
      {error && <span className="text-xs text-red-400 font-mono">{error}</span>}
      <button
        onClick={handleRun}
        disabled={running}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-ws-green text-[#0a0f1a] text-sm font-semibold hover:bg-ws-green-dim transition-colors disabled:opacity-50 cursor-pointer"
      >
        {running ? (
          <div className="w-4 h-4 border-2 border-[#0a0f1a]/30 border-t-[#0a0f1a] rounded-full animate-spin" />
        ) : (
          <HiOutlinePlay className="w-4 h-4" />
        )}
        {running ? 'Running...' : 'Run Analysis Now'}
      </button>
    </div>
  );
}
