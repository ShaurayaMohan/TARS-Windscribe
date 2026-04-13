import { useState } from 'react';
import { HiOutlineMagnifyingGlass, HiOutlineXMark } from 'react-icons/hi2';

interface Props {
  onApply: (fromDate: string, toDate: string) => void;
  onClear: () => void;
  hasActiveFilter: boolean;
}

export default function DateRangeFilter({ onApply, onClear, hasActiveFilter }: Props) {
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const today = new Date().toISOString().split('T')[0];

  function handleFromChange(val: string) {
    setFrom(val);
    if (to && val > to) setTo(val);
  }

  function handleToChange(val: string) {
    setTo(val);
    if (from && val < from) setFrom(val);
  }

  function handleApply() {
    if (!from && !to) return;
    onApply(from, to);
  }

  function handleClear() {
    setFrom('');
    setTo('');
    onClear();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') handleApply();
  }

  const canApply = from || to;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-mono uppercase tracking-wider text-ws-muted">From</span>
        <input
          type="date"
          value={from}
          max={to || today}
          onChange={(e) => handleFromChange(e.target.value)}
          onKeyDown={handleKeyDown}
          className="rounded-lg px-3 py-1.5 text-sm bg-white/[0.04] border border-ws-border/60 text-ws-text focus:outline-none focus:border-ws-green/50 transition-colors"
        />
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-mono uppercase tracking-wider text-ws-muted">To</span>
        <input
          type="date"
          value={to}
          min={from || undefined}
          max={today}
          onChange={(e) => handleToChange(e.target.value)}
          onKeyDown={handleKeyDown}
          className="rounded-lg px-3 py-1.5 text-sm bg-white/[0.04] border border-ws-border/60 text-ws-text focus:outline-none focus:border-ws-green/50 transition-colors"
        />
      </div>
      <button
        onClick={handleApply}
        disabled={!canApply}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-ws-green/15 text-ws-green text-xs font-mono font-medium border border-ws-green/30 hover:bg-ws-green/25 transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
      >
        <HiOutlineMagnifyingGlass className="w-3.5 h-3.5" />
        Apply
      </button>
      {hasActiveFilter && (
        <button
          onClick={handleClear}
          className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-mono text-ws-muted hover:text-ws-text hover:bg-white/[0.05] transition-colors cursor-pointer"
        >
          <HiOutlineXMark className="w-3.5 h-3.5" />
          Clear
        </button>
      )}
    </div>
  );
}
