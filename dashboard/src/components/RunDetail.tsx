import { useState } from 'react';
import type { Analysis } from '../api';
import { HiOutlineArrowTrendingUp, HiOutlineChevronDown, HiOutlineChevronUp } from 'react-icons/hi2';

interface Props {
  analysis: Analysis | null;
  loading: boolean;
}

const INITIAL_SHOW = 5;

export default function RunDetail({ analysis, loading }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[0, 1].map((i) => (
          <div key={i} className="glass-card rounded-xl p-6 animate-fade-in" style={{ animationDelay: `${i * 80}ms` }}>
            <div className="h-6 w-32 rounded bg-ws-border/50 animate-pulse mb-4" />
            <div className="space-y-3">
              {[0, 1, 2].map((j) => (
                <div key={j} className="h-12 rounded bg-ws-border/30 animate-pulse" />
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="glass-card rounded-xl p-12 text-center animate-fade-in">
        <p className="font-mono text-sm text-ws-muted">Select a run to view details</p>
      </div>
    );
  }

  const categories = Object.entries(analysis.categories)
    .map(([id, cat]) => ({ id, ...cat }))
    .sort((a, b) => b.count - a.count);

  const visibleCategories = expanded ? categories : categories.slice(0, INITIAL_SHOW);
  const hiddenCount = categories.length - INITIAL_SHOW;
  const trends = analysis.new_trends;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="glass-card rounded-xl p-6 animate-fade-in">
        <h3 className="font-mono text-[11px] uppercase tracking-wider text-ws-muted mb-4">
          Categories <span className="text-ws-text">({categories.length})</span>
        </h3>
        {categories.length === 0 ? (
          <p className="text-sm text-ws-muted text-center py-8">No categories found</p>
        ) : (
          <>
            <div className="space-y-1">
              {visibleCategories.map((cat) => (
                <div
                  key={cat.id}
                  className="flex items-start gap-3 rounded-lg px-3 py-2.5 hover:bg-white/[0.03] transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm text-ws-text font-medium truncate">{cat.title}</span>
                      <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-ws-green/10 text-ws-green flex-shrink-0">
                        {cat.count}
                      </span>
                    </div>
                    <p className="text-xs text-ws-muted mt-0.5 truncate">{cat.summary}</p>
                  </div>
                </div>
              ))}
            </div>
            {hiddenCount > 0 && (
              <button
                onClick={() => setExpanded((v) => !v)}
                className="mt-3 w-full flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-mono text-ws-muted hover:text-ws-green hover:bg-ws-green/[0.05] transition-colors cursor-pointer"
              >
                {expanded ? (
                  <>Show less <HiOutlineChevronUp className="w-3.5 h-3.5" /></>
                ) : (
                  <>Show {hiddenCount} more <HiOutlineChevronDown className="w-3.5 h-3.5" /></>
                )}
              </button>
            )}
          </>
        )}
      </div>

      <div className="glass-card rounded-xl p-6 animate-fade-in" style={{ animationDelay: '80ms' }}>
        <h3 className="font-mono text-[11px] uppercase tracking-wider text-ws-muted mb-4">
          New Trends <span className="text-ws-text">({trends.length})</span>
        </h3>
        {trends.length === 0 ? (
          <p className="text-sm text-ws-muted text-center py-8">No new trends detected</p>
        ) : (
          <div className="space-y-3">
            {trends.map((trend, i) => (
              <div
                key={i}
                className="rounded-lg px-3 py-3 bg-white/[0.02] border border-ws-border/40"
              >
                <div className="flex items-start gap-2.5">
                  <HiOutlineArrowTrendingUp className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm text-ws-text font-medium">{trend.title}</span>
                      <span className="text-[10px] font-mono text-ws-muted bg-white/[0.06] px-1.5 py-0.5 rounded">
                        {trend.count} tickets
                      </span>
                      {trend.geographic_pattern && (
                        <span className="text-[10px] font-mono text-ws-muted italic bg-white/[0.04] px-1.5 py-0.5 rounded">
                          {trend.geographic_pattern}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-ws-muted mt-1 leading-relaxed">{trend.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
