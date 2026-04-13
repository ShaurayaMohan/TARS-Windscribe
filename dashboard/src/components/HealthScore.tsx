import { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import type { SentimentResponse } from '../api';
import { HiOutlineQuestionMarkCircle } from 'react-icons/hi2';

interface Props {
  data: SentimentResponse | null;
  loading: boolean;
}

function getHealthColor(score: number): string {
  if (score >= 80) return '#22c55e';
  if (score >= 60) return '#00d09c';
  if (score >= 40) return '#f59e0b';
  return '#ef4444';
}

export default function HealthScore({ data, loading }: Props) {
  const [hovered, setHovered] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);

  const score = data?.health_score ?? 0;
  const label = data?.health_label ?? '\u2014';
  const color = getHealthColor(score);

  const rect = btnRef.current?.getBoundingClientRect();

  return (
    <div className="glass-card rounded-xl p-5 animate-fade-in">
      <div className="flex items-center gap-4 flex-wrap">
        <span className="font-mono text-sm text-ws-muted whitespace-nowrap">Customer Health Score:</span>
        {loading ? (
          <div className="h-8 w-24 rounded bg-ws-border/50 animate-pulse" />
        ) : (
          <>
            <span className="text-2xl font-mono font-bold" style={{ color }}>
              {score}
            </span>
            <span className="text-ws-muted font-mono text-sm">/ 100</span>
            <div className="flex-1 min-w-[120px] max-w-md">
              <div className="h-2.5 rounded-full bg-ws-border/50 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-1000 ease-out"
                  style={{ width: `${score}%`, backgroundColor: color }}
                />
              </div>
            </div>
            <span
              className="text-xs font-mono font-medium px-2.5 py-1 rounded-full"
              style={{ color, background: `${color}20` }}
            >
              {label}
            </span>
          </>
        )}
        <button
          ref={btnRef}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          className="text-ws-muted hover:text-ws-text transition-colors cursor-pointer"
        >
          <HiOutlineQuestionMarkCircle className="w-5 h-5" />
        </button>
      </div>

      {hovered && rect && createPortal(
        <div
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          className="fixed w-80 rounded-xl p-5 shadow-2xl shadow-black/50 border border-ws-border/80 animate-scale-in"
          style={{
            top: rect.bottom + 8,
            right: window.innerWidth - rect.right,
            zIndex: 9999,
            background: 'rgba(17, 24, 39, 0.97)',
          }}
        >
          <p className="font-mono text-xs font-semibold text-ws-text mb-2.5">
            How is this calculated?
          </p>
          <p className="text-xs text-ws-muted mb-3 leading-relaxed">
            Score = 100 &minus; (sentiment penalty + urgency penalty + churn penalty)
          </p>
          <div className="space-y-2 text-xs text-ws-muted leading-relaxed">
            <p>
              <span className="text-ws-text font-medium">Sentiment</span> (max 40 pts):
              positive 0, neutral/confused 10, frustrated 30, angry 40
            </p>
            <p>
              <span className="text-ws-text font-medium">Urgency</span> (max 30 pts):
              low 0, medium 10, high 20, critical 30
            </p>
            <p>
              <span className="text-ws-text font-medium">Churn risk</span> (max 30 pts):
              low 0, medium 15, high 30
            </p>
          </div>
          <p className="text-[11px] text-ws-muted mt-3 pt-3 border-t border-ws-border leading-relaxed">
            Each penalty is the weighted average across all scored tickets, scaled to its max.
          </p>
        </div>,
        document.body,
      )}
    </div>
  );
}
