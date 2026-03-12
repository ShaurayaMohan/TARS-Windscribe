import React, { useEffect, useState, useCallback } from 'react';
import { FiTrendingUp, FiTag, FiRefreshCw, FiFileText, FiLoader } from 'react-icons/fi';
import SpotlightCard from './SpotlightCard';
import Dock from './Dock';
import type { DockItemData } from './Dock';
import { fetchAnalyses, triggerAnalysis, timeAgo, sortedCategories, type Analysis } from '../api';

// ─── Types ────────────────────────────────────────────────────────────────────
type View = 'trends' | 'categories';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildSummary(latest: Analysis): string {
  const cats = sortedCategories(latest);
  const top = cats[0];
  const catCount = cats.length;
  const trendCount = latest.new_trends.length;
  return (
    `Analyzed ${latest.total_tickets.toLocaleString()} tickets across ` +
    `${catCount} categories. Top issue: "${top?.title ?? 'N/A'}"` +
    ` with ${top?.count ?? 0} tickets.` +
    (trendCount > 0 ? ` ${trendCount} new trend${trendCount > 1 ? 's' : ''} detected.` : '')
  );
}

function buildSpikes(latest: Analysis, previous: Analysis) {
  const prevCats = sortedCategories(previous);
  const prevMap = new Map(prevCats.map((c) => [c.title, c.count]));

  const latestCats = sortedCategories(latest);
  const spikes = latestCats
    .filter((c) => prevMap.has(c.title) && prevMap.get(c.title)! > 0)
    .map((c) => {
      const prev = prevMap.get(c.title)!;
      const pct = Math.round(((c.count - prev) / prev) * 100);
      return { label: c.title, pct, count: c.count };
    })
    .filter((s) => s.pct > 0)
    .sort((a, b) => b.pct - a.pct)
    .slice(0, 3);

  if (spikes.length === 0) {
    return latestCats.slice(0, 3).map((c) => ({
      label: c.title,
      pct: null as number | null,
      count: c.count,
    }));
  }
  return spikes;
}

const SPIKE_COLORS = ['#EF5350', '#FFA726', '#FFCA28'];

function buildTags(latest: Analysis): string[] {
  const keywords = new Set<string>();
  const stopwords = new Set(['and', 'in', 'on', 'at', 'the', 'for', 'with', 'to', 'of', 'a', 'an', 'by', 'not', 'no']);
  for (const cat of sortedCategories(latest)) {
    cat.title
      .split(/[\s\/\-]+/)
      .map((w) => w.replace(/[^a-zA-Z]/g, '').toLowerCase())
      .filter((w) => w.length > 3 && !stopwords.has(w))
      .forEach((w) => keywords.add(`#${w}`));
  }
  return [...keywords].slice(0, 8);
}

// ─── Sub-views ────────────────────────────────────────────────────────────────

const DOCK_HEIGHT = 48;

interface TrendsViewProps {
  latest: Analysis;
  previous: Analysis | null;
}

const TrendsView: React.FC<TrendsViewProps> = ({ latest, previous }) => {
  const summary = buildSummary(latest);
  const spikes = previous ? buildSpikes(latest, previous) : [];
  const topIssues = sortedCategories(latest).slice(0, 3);
  const tags = buildTags(latest);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '9px' }}>

      <div style={{
        background: 'rgba(71, 248, 199, 0.06)',
        border: '1px solid rgba(71, 248, 199, 0.15)',
        borderRadius: '8px',
        padding: '8px 12px',
        flexShrink: 0,
      }}>
        <p style={{ color: 'rgba(255,255,255,0.82)', margin: 0, fontSize: '12px', lineHeight: '1.55' }}>
          {summary}
        </p>
      </div>

      <div style={{ display: 'flex', gap: '12px', flexShrink: 0 }}>

        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ color: 'rgba(255,255,255,0.45)', margin: '0 0 5px 0', fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' }}>
            Trending Spikes
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {spikes.length === 0 ? (
              <p style={{ color: 'rgba(255,255,255,0.35)', fontSize: '11px', margin: 0 }}>Need 2+ analyses to compare</p>
            ) : spikes.map((spike, i) => (
              <div key={spike.label} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                background: 'rgba(255,255,255,0.03)', borderRadius: '7px', padding: '5px 9px',
              }}>
                <span style={{ color: 'rgba(255,255,255,0.78)', fontSize: '11px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, marginRight: 6 }}>
                  {spike.label}
                </span>
                <span style={{
                  color: SPIKE_COLORS[i],
                  fontSize: '10px', fontWeight: 700,
                  background: `${SPIKE_COLORS[i]}18`,
                  border: `1px solid ${SPIKE_COLORS[i]}44`,
                  borderRadius: '5px', padding: '1px 6px', flexShrink: 0,
                }}>
                  {spike.pct !== null ? `↑ ${spike.pct}%` : `${spike.count} tickets`}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ color: 'rgba(255,255,255,0.45)', margin: '0 0 5px 0', fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' }}>
            Top Issues
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {topIssues.map((item, i) => (
              <div key={item.title} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '5px 7px', borderRadius: '7px', background: 'rgba(255,255,255,0.03)' }}>
                <span style={{
                  width: '18px', height: '18px', borderRadius: '50%',
                  background: 'rgba(71, 248, 199, 0.15)',
                  border: '1px solid rgba(71, 248, 199, 0.3)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '9px', fontWeight: 700, color: '#47f8c7', flexShrink: 0,
                }}>
                  {i + 1}
                </span>
                <span style={{ flex: 1, color: 'rgba(255,255,255,0.82)', fontSize: '11px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {item.title}
                </span>
                <span style={{
                  background: 'rgba(71, 248, 199, 0.12)',
                  border: '1px solid rgba(71, 248, 199, 0.25)',
                  borderRadius: '10px', padding: '1px 7px',
                  fontSize: '10px', fontWeight: 600, color: '#47f8c7', flexShrink: 0,
                }}>
                  {item.count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ flexShrink: 0 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
          {tags.map((tag) => (
            <span
              key={tag}
              style={{
                background: 'rgba(71, 248, 199, 0.08)',
                border: '1px solid rgba(71, 248, 199, 0.2)',
                borderRadius: '20px', padding: '2px 9px',
                fontSize: '10px', color: 'rgba(71, 248, 199, 0.9)',
                cursor: 'default', transition: 'all 0.2s',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.background = 'rgba(71,248,199,0.2)';
                (e.currentTarget as HTMLElement).style.borderColor = 'rgba(71,248,199,0.5)';
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.background = 'rgba(71,248,199,0.08)';
                (e.currentTarget as HTMLElement).style.borderColor = 'rgba(71,248,199,0.2)';
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

// ─── Categories View ──────────────────────────────────────────────────────────
const CategoriesView: React.FC<{ latest: Analysis }> = ({ latest }) => {
  const cats = sortedCategories(latest);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', overflowY: 'auto', maxHeight: '220px', paddingRight: '2px' }}>
      {cats.map((cat, i) => (
        <div
          key={cat.id}
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(71, 248, 199, 0.1)',
            borderRadius: '8px',
            padding: '8px 10px',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{
              width: '20px', height: '20px', borderRadius: '50%',
              background: 'rgba(71, 248, 199, 0.15)',
              border: '1px solid rgba(71, 248, 199, 0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '9px', fontWeight: 700, color: '#47f8c7', flexShrink: 0,
            }}>
              {i + 1}
            </span>
            <span style={{ flex: 1, color: 'rgba(255,255,255,0.92)', fontSize: '12px', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {cat.title}
            </span>
            <span style={{
              background: 'rgba(71, 248, 199, 0.12)',
              border: '1px solid rgba(71, 248, 199, 0.25)',
              borderRadius: '10px', padding: '1px 8px',
              fontSize: '10px', fontWeight: 700, color: '#47f8c7', flexShrink: 0,
            }}>
              {cat.count}
            </span>
          </div>
          {cat.summary && (
            <p style={{
              color: 'rgba(255,255,255,0.5)', fontSize: '10px', margin: 0,
              lineHeight: '1.4', overflow: 'hidden',
              display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
            }}>
              {cat.summary}
            </p>
          )}
        </div>
      ))}
    </div>
  );
};

// ─── Loading / Empty ──────────────────────────────────────────────────────────
const PlaceholderContent: React.FC<{ loading: boolean }> = ({ loading }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '140px', opacity: 0.4 }}>
    {loading ? (
      <div style={{
        width: '32px', height: '32px', borderRadius: '50%',
        border: '3px solid rgba(71,248,199,0.2)',
        borderTop: '3px solid #47f8c7',
        animation: 'spin 1s linear infinite',
      }} />
    ) : (
      <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px', margin: 0 }}>
        No analyses found. Run TARS to populate.
      </p>
    )}
  </div>
);

// ─── Main Component ───────────────────────────────────────────────────────────
const AIInsightsPanel: React.FC = () => {
  const [view, setView] = useState<View>('trends');
  const [latest, setLatest] = useState<Analysis | null>(null);
  const [previous, setPrevious] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [reanalyzeMsg, setReanalyzeMsg] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchAnalyses(2);
      const list = result?.analyses ?? [];
      if (list.length >= 1) setLatest(list[0]);
      if (list.length >= 2) setPrevious(list[1]);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleReanalyze = useCallback(async () => {
    if (reanalyzing) return;
    setReanalyzing(true);
    setReanalyzeMsg(null);
    try {
      const res = await triggerAnalysis(24);
      setReanalyzeMsg(res.status === 'success' ? 'Done!' : 'Failed');
      if (res.status === 'success') {
        await loadData();
      }
    } catch {
      setReanalyzeMsg('Error');
    } finally {
      setReanalyzing(false);
      setTimeout(() => setReanalyzeMsg(null), 3000);
    }
  }, [reanalyzing, loadData]);

  const dockItems: DockItemData[] = [
    {
      icon: <FiTrendingUp size={16} />,
      label: 'Trends',
      onClick: () => setView('trends'),
      className: view === 'trends' ? 'dock-item-active' : '',
    },
    {
      icon: <FiTag size={16} />,
      label: 'Categories',
      onClick: () => setView('categories'),
      className: view === 'categories' ? 'dock-item-active' : '',
    },
    {
      icon: reanalyzing ? <FiLoader size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <FiRefreshCw size={16} />,
      label: reanalyzeMsg ?? (reanalyzing ? 'Running…' : 'Re-analyze'),
      onClick: handleReanalyze,
    },
    {
      icon: <FiFileText size={16} />,
      label: 'Report',
      onClick: () => {},
      className: 'dock-item-disabled',
    },
  ];

  const lastRunText = latest
    ? `POWERED BY TARS · ${timeAgo(latest.run_date).toUpperCase()}`
    : 'POWERED BY TARS';

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .dock-item-active {
          border-color: rgba(71, 248, 199, 0.6) !important;
          background: rgba(71, 248, 199, 0.12) !important;
          color: #47f8c7 !important;
        }
        .dock-item-disabled {
          opacity: 0.35 !important;
          cursor: not-allowed !important;
        }
      `}</style>

      <div style={{ flex: 1, minHeight: 0, overflow: 'visible' }}>
        <SpotlightCard
          className="custom-spotlight-card spotlight-compact"
          spotlightColor="rgba(71, 248, 199, 0.2)"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '9px' }}>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <h3 style={{ color: '#47f8c7', margin: '0 0 2px 0', fontSize: '16px', fontWeight: 600 }}>
                  AI Insights
                </h3>
                <p style={{ color: 'rgba(255,255,255,0.4)', margin: 0, fontSize: '10px', letterSpacing: '0.5px' }}>
                  {lastRunText}
                </p>
              </div>
              <span style={{
                fontSize: '9px', fontWeight: 700, letterSpacing: '0.8px',
                color: '#47f8c7', background: 'rgba(71,248,199,0.1)',
                border: '1px solid rgba(71,248,199,0.25)',
                borderRadius: '6px', padding: '2px 7px', textTransform: 'uppercase',
              }}>
                {view}
              </span>
            </div>

            {loading || !latest ? (
              <PlaceholderContent loading={loading} />
            ) : view === 'trends' ? (
              <TrendsView latest={latest} previous={previous} />
            ) : (
              <CategoriesView latest={latest} />
            )}

          </div>
        </SpotlightCard>
      </div>

      <div style={{
        height: `${DOCK_HEIGHT}px`,
        flexShrink: 0,
        position: 'relative',
        overflow: 'visible',
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'center',
        marginTop: '12px',
      }}>
        <Dock
          items={dockItems}
          panelHeight={DOCK_HEIGHT - 4}
          baseItemSize={36}
          magnification={52}
          distance={110}
        />
      </div>

    </div>
  );
};

export default AIInsightsPanel;
