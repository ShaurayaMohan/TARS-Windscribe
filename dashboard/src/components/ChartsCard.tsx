import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { createPortal } from 'react-dom';
import CardSwap, { Card } from './CardSwap';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { fetchTrends, fetchAnalyses, sortedCategories, type TrendsResponse, type Analysis } from '../api';

// ─── Palette for stacked bars ─────────────────────────────────────────────────
const STACK_COLORS = [
  '#47f8c7', '#36c5a0', '#2a9d7e', '#f5a623', '#e06c75',
  '#61afef', '#c678dd', '#56b6c2', '#98c379', '#d19a66',
];

// ─── Shared tooltip style ────────────────────────────────────────────────────
const tooltipStyle = {
  contentStyle: {
    backgroundColor: 'rgba(10, 25, 41, 0.95)',
    border: '1px solid rgba(71, 248, 199, 0.3)',
    borderRadius: '8px',
    color: '#fff',
    fontSize: '13px',
  },
};

const axisStyle = {
  stroke: 'rgba(255,255,255,0.6)',
  style: { fontSize: '11px' },
  tick: { fill: 'rgba(255,255,255,0.6)' },
};

// ─── Chart 1: Ticket Volume Over Time (30 days) ─────────────────────────────
interface VolumePoint { date: string; tickets: number; }

const TicketVolumeChart: React.FC<{ data: VolumePoint[]; loading: boolean }> = ({ data, loading }) => (
  <div style={{ width: '100%', height: '100%', padding: '24px', display: 'flex', flexDirection: 'column' }}>
    <h3 style={{ color: '#47f8c7', margin: '0 0 16px 0', fontSize: '18px', fontWeight: 600 }}>
      Ticket Volume Over Time
    </h3>
    {loading || data.length === 0 ? (
      <EmptyChart loading={loading} label="No volume data yet" />
    ) : (
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorTickets" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#47f8c7" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#47f8c7" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(71, 248, 199, 0.1)" />
          <XAxis dataKey="date" {...axisStyle} />
          <YAxis {...axisStyle} />
          <Tooltip {...tooltipStyle} />
          <Area type="monotone" dataKey="tickets" stroke="#47f8c7" strokeWidth={2}
            fillOpacity={1} fill="url(#colorTickets)" />
        </AreaChart>
      </ResponsiveContainer>
    )}
  </div>
);

// ─── Chart 2: Ticket Volume by Category (last 7 days, stacked bar) ───────────

const StackedTooltip: React.FC<{ active?: boolean; payload?: Array<{ value: unknown; dataKey: string; color: string }>; label?: string }> = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;
  const total = payload.reduce((sum, p) => sum + ((p.value as number) || 0), 0);
  return (
    <div style={{
      backgroundColor: 'rgba(10, 25, 41, 0.95)',
      border: '1px solid rgba(71, 248, 199, 0.3)',
      borderRadius: '8px',
      padding: '10px 14px',
      fontSize: '12px',
    }}>
      <p style={{ color: '#47f8c7', margin: '0 0 6px 0', fontWeight: 600 }}>{label} — {total} tickets</p>
      {payload
        .filter((p) => (p.value as number) > 0)
        .sort((a, b) => ((b.value as number) || 0) - ((a.value as number) || 0))
        .map((p) => (
          <p key={p.dataKey} style={{ margin: '2px 0', color: 'rgba(255,255,255,0.8)' }}>
            <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, backgroundColor: p.color, marginRight: 6 }} />
            {p.dataKey}: {p.value}
          </p>
        ))}
    </div>
  );
};

interface StackedBarProps {
  data: Record<string, unknown>[];
  categoryKeys: string[];
  loading: boolean;
}

const TicketsByCategoryChart: React.FC<StackedBarProps> = ({ data, categoryKeys, loading }) => (
  <div style={{ width: '100%', height: '100%', padding: '24px', display: 'flex', flexDirection: 'column' }}>
    <h3 style={{ color: '#47f8c7', margin: '0 0 16px 0', fontSize: '18px', fontWeight: 600 }}>
      Volume by Category (7d)
    </h3>
    {loading || data.length === 0 ? (
      <EmptyChart loading={loading} label="No category breakdown yet" />
    ) : (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(71, 248, 199, 0.1)" />
          <XAxis dataKey="date" {...axisStyle} />
          <YAxis {...axisStyle} />
          <Tooltip content={<StackedTooltip />} />
          {categoryKeys.map((key, i) => (
            <Bar
              key={key}
              dataKey={key}
              stackId="categories"
              fill={STACK_COLORS[i % STACK_COLORS.length]}
              radius={i === categoryKeys.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    )}
  </div>
);

// ─── Chart 3: Top Recurring Issues ───────────────────────────────────────────
interface TopIssuePoint { title: string; count: number; }

const TopIssuesChart: React.FC<{ data: TopIssuePoint[]; loading: boolean }> = ({ data, loading }) => (
  <div style={{ width: '100%', height: '100%', padding: '24px', display: 'flex', flexDirection: 'column' }}>
    <h3 style={{ color: '#47f8c7', margin: '0 0 16px 0', fontSize: '18px', fontWeight: 600 }}>
      Top Recurring Issues
    </h3>
    {loading || data.length === 0 ? (
      <EmptyChart loading={loading} label="No recurring issues yet" />
    ) : (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(71, 248, 199, 0.1)" horizontal={false} />
          <XAxis type="number" {...axisStyle} allowDecimals={false} />
          <YAxis
            type="category"
            dataKey="title"
            width={140}
            tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 11 }}
            tickFormatter={(v: string) => v.length > 18 ? v.slice(0, 16) + '…' : v}
          />
          <Tooltip {...tooltipStyle} />
          <Bar dataKey="count" radius={[0, 6, 6, 0]}>
            {data.map((_, i) => (
              <Cell
                key={i}
                fill={`rgba(71, 248, 199, ${0.9 - i * 0.08})`}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    )}
  </div>
);

// ─── Empty / Loading state ────────────────────────────────────────────────────
const EmptyChart: React.FC<{ loading: boolean; label: string }> = ({ loading, label }) => (
  <div style={{
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'column',
    gap: '8px',
    opacity: 0.45,
  }}>
    {loading ? (
      <div style={{
        width: '40px', height: '40px', borderRadius: '50%',
        border: '3px solid rgba(71,248,199,0.2)',
        borderTop: '3px solid #47f8c7',
        animation: 'spin 1s linear infinite',
      }} />
    ) : (
      <>
        <span style={{ fontSize: '28px' }}>📊</span>
        <p style={{ color: 'rgba(255,255,255,0.6)', margin: 0, fontSize: '13px' }}>{label}</p>
        <p style={{ color: 'rgba(255,255,255,0.35)', margin: 0, fontSize: '11px' }}>Run an analysis to populate</p>
      </>
    )}
  </div>
);

// ─── Expanded Chart Modal ─────────────────────────────────────────────────────
const ChartModal: React.FC<{ children: React.ReactNode; onClose: () => void }> = ({ children, onClose }) => {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  return createPortal(
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        animation: 'chartModalFadeIn 0.25s ease-out',
      }}
    >
      <style>{`
        @keyframes chartModalFadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes chartModalScaleIn {
          from { opacity: 0; transform: scale(0.92); }
          to   { opacity: 1; transform: scale(1); }
        }
      `}</style>
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '80vw',
          maxWidth: '1100px',
          height: '70vh',
          maxHeight: '650px',
          background: 'rgba(10, 22, 40, 0.75)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          border: '1px solid rgba(71, 248, 199, 0.2)',
          borderRadius: '20px',
          boxShadow: '0 8px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(71, 248, 199, 0.08)',
          position: 'relative',
          animation: 'chartModalScaleIn 0.3s ease-out',
          overflow: 'hidden',
        }}
      >
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            zIndex: 10,
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            border: '1px solid rgba(71, 248, 199, 0.3)',
            background: 'rgba(71, 248, 199, 0.08)',
            color: 'rgba(255,255,255,0.7)',
            fontSize: '16px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(71, 248, 199, 0.2)';
            e.currentTarget.style.color = '#fff';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(71, 248, 199, 0.08)';
            e.currentTarget.style.color = 'rgba(255,255,255,0.7)';
          }}
        >
          ✕
        </button>

        {children}
      </div>
    </div>,
    document.body,
  );
};

// ─── Transform helpers ────────────────────────────────────────────────────────
function toVolumeData(breakdown: TrendsResponse['daily_breakdown'] | null | undefined): VolumePoint[] {
  if (!breakdown) return [];
  return Object.entries(breakdown)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, val]) => ({
      date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      tickets: val.tickets,
    }));
}

/** Build stacked bar data from analyses (last 7 days). Uses categories dict. */
function toStackedData(analyses: Analysis[]): { data: Record<string, unknown>[]; keys: string[] } {
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 7);

  const recent = analyses.filter((a) => new Date(a.run_date) >= cutoff);
  if (recent.length === 0) return { data: [], keys: [] };

  const allTitles = new Set<string>();
  const dayMap = new Map<string, Record<string, unknown>>();

  for (const analysis of recent) {
    const dateLabel = new Date(analysis.run_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

    if (!dayMap.has(dateLabel)) {
      dayMap.set(dateLabel, { date: dateLabel });
    }
    const row = dayMap.get(dateLabel)!;

    for (const cat of sortedCategories(analysis)) {
      allTitles.add(cat.title);
      row[cat.title] = ((row[cat.title] as number) || 0) + cat.count;
    }
  }

  const sortedDates = [...recent]
    .sort((a, b) => new Date(a.run_date).getTime() - new Date(b.run_date).getTime())
    .map((a) => new Date(a.run_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));

  const uniqueDates = [...new Set(sortedDates)];

  const data = uniqueDates.map((d) => {
    const row = dayMap.get(d) || { date: d };
    for (const title of allTitles) {
      if (!(title in row)) row[title] = 0;
    }
    return row;
  });

  const keys = [...allTitles].sort((a, b) => {
    const sumA = data.reduce((s, r) => s + ((r[a] as number) || 0), 0);
    const sumB = data.reduce((s, r) => s + ((r[b] as number) || 0), 0);
    return sumB - sumA;
  });

  return { data, keys };
}

// ─── ChartsCard ───────────────────────────────────────────────────────────────
const ChartsCard: React.FC = () => {
  const [trends, setTrends]       = useState<TrendsResponse | null>(null);
  const [analyses, setAnalyses]   = useState<Analysis[]>([]);
  const [loading, setLoading]     = useState(true);
  const [expandedChart, setExpandedChart] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      fetchTrends(30),
      fetchAnalyses(30),
    ])
      .then(([trendsData, analysesData]) => {
        if (cancelled) return;
        setTrends(trendsData);
        setAnalyses(analysesData?.analyses ?? []);
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  const volumeData  = trends?.daily_breakdown ? toVolumeData(trends.daily_breakdown) : [];
  const topIssues   = trends?.top_recurring_issues ? trends.top_recurring_issues.slice(0, 8) : [];

  const { data: stackedData, keys: categoryKeys } = useMemo(
    () => toStackedData(analyses),
    [analyses],
  );

  const handleCardClick = useCallback((index: number) => {
    setExpandedChart(index);
  }, []);

  const closeModal = useCallback(() => {
    setExpandedChart(null);
  }, []);

  const renderExpandedChart = () => {
    switch (expandedChart) {
      case 0: return <TicketVolumeChart data={volumeData} loading={loading} />;
      case 1: return <TicketsByCategoryChart data={stackedData} categoryKeys={categoryKeys} loading={loading} />;
      case 2: return <TopIssuesChart data={topIssues} loading={loading} />;
      default: return null;
    }
  };

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
      <CardSwap
        cardDistance={30}
        verticalDistance={35}
        delay={5000}
        pauseOnHover={true}
        onCardClick={handleCardClick}
        skewAmount={0}
        width={500}
        height={400}
      >
        <Card style={{ cursor: 'pointer' }}>
          <TicketVolumeChart data={volumeData} loading={loading} />
        </Card>
        <Card style={{ cursor: 'pointer' }}>
          <TicketsByCategoryChart data={stackedData} categoryKeys={categoryKeys} loading={loading} />
        </Card>
        <Card style={{ cursor: 'pointer' }}>
          <TopIssuesChart data={topIssues} loading={loading} />
        </Card>
      </CardSwap>

      {expandedChart !== null && (
        <ChartModal onClose={closeModal}>
          {renderExpandedChart()}
        </ChartModal>
      )}
    </div>
  );
};

export default ChartsCard;
