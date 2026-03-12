import React, { useEffect, useState, useMemo } from 'react';
import SpotlightCard from './SpotlightCard';
import { fetchAnalyses, sortedCategories, type Analysis } from '../api';

function makeSummary(analysis: Analysis): string {
  const cats = sortedCategories(analysis);
  if (cats.length === 0) return 'No categories identified';
  return cats.slice(0, 4).map((c) => c.title).join(' · ');
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

const TIME_OPTIONS = [
  { value: '1',  label: '1 Day'   },
  { value: '7',  label: '7 Days'  },
  { value: '30', label: '30 Days' },
  { value: '90', label: '90 Days' },
];

const RecentAnalysesCard: React.FC = () => {
  const [analyses, setAnalyses]   = useState<Analysis[]>([]);
  const [loading, setLoading]     = useState(true);
  const [timeFrame, setTimeFrame] = useState('7');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetchAnalyses(200)
      .then(({ analyses: data }) => {
        if (!cancelled) {
          setAnalyses(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  const filtered = useMemo(() => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - parseInt(timeFrame));
    return analyses.filter((a) => new Date(a.run_date) >= cutoff);
  }, [analyses, timeFrame]);

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: '12px', minHeight: 0 }}>
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <SpotlightCard className="custom-spotlight-card spotlight-fill" spotlightColor="rgba(71, 248, 199, 0.2)">
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

            {/* Header */}
            <div style={{ marginBottom: '16px' }}>
              <h3 style={{ color: '#47f8c7', margin: '0 0 4px 0', fontSize: '18px', fontWeight: 600 }}>
                Recent Analyses
              </h3>
              <p style={{ color: 'rgba(255,255,255,0.6)', margin: 0, fontSize: '13px' }}>
                {loading
                  ? 'Loading…'
                  : filtered.length === 0
                    ? `No analyses in the last ${timeFrame} ${timeFrame === '1' ? 'day' : 'days'}`
                    : `${filtered.length} run${filtered.length !== 1 ? 's' : ''} · last ${timeFrame} ${timeFrame === '1' ? 'day' : 'days'}`}
              </p>
            </div>

            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <div style={{ flex: 1, overflow: 'auto' }}>
                {loading ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', paddingTop: '8px' }}>
                    {[1, 2, 3].map((i) => (
                      <div key={i} style={{
                        height: '44px',
                        borderRadius: '8px',
                        background: 'rgba(71, 248, 199, 0.05)',
                        animation: 'pulse 1.5s ease-in-out infinite',
                        opacity: 1 - i * 0.2,
                      }} />
                    ))}
                  </div>
                ) : filtered.length === 0 ? (
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100%',
                    gap: '8px',
                    opacity: 0.5,
                  }}>
                    <span style={{ fontSize: '32px' }}>📭</span>
                    <p style={{ color: 'rgba(255,255,255,0.6)', margin: 0, fontSize: '13px' }}>
                      No analyses found for this period
                    </p>
                  </div>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid rgba(71, 248, 199, 0.2)' }}>
                        <th style={{ textAlign: 'left', padding: '12px 16px 12px 0', color: '#47f8c7', fontSize: '14px', fontWeight: 600, whiteSpace: 'nowrap' }}>Date</th>
                        <th style={{ textAlign: 'left', padding: '12px 24px 12px 0', color: '#47f8c7', fontSize: '14px', fontWeight: 600, whiteSpace: 'nowrap' }}>Tickets</th>
                        <th style={{ textAlign: 'left', padding: '12px 0',           color: '#47f8c7', fontSize: '14px', fontWeight: 600, width: '100%' }}>Summary</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((a) => (
                        <tr
                          key={a._id}
                          style={{ borderBottom: '1px solid rgba(71, 248, 199, 0.1)', transition: 'background-color 0.2s' }}
                          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(71, 248, 199, 0.05)'; }}
                          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
                        >
                          <td style={{ padding: '14px 0', color: 'rgba(255,255,255,0.9)', fontSize: '13px', whiteSpace: 'nowrap', paddingRight: '16px' }}>
                            {formatDate(a.run_date)}
                          </td>
                          <td style={{ padding: '14px 0', color: 'rgba(255,255,255,0.9)', fontSize: '13px', paddingRight: '16px' }}>
                            {a.total_tickets.toLocaleString()}
                          </td>
                          <td style={{ padding: '14px 0', color: 'rgba(255,255,255,0.6)', fontSize: '13px' }}>
                            {makeSummary(a)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        </SpotlightCard>
      </div>

      {/* Time Dial */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', padding: '8px 0', flexShrink: 0 }}>
        {TIME_OPTIONS.map((option) => (
          <button
            key={option.value}
            onClick={() => setTimeFrame(option.value)}
            style={{
              padding: '10px 20px',
              background: timeFrame === option.value ? 'rgba(71, 248, 199, 0.25)' : 'rgba(71, 248, 199, 0.08)',
              border: `2px solid ${timeFrame === option.value ? '#47f8c7' : 'rgba(71, 248, 199, 0.3)'}`,
              borderRadius: '24px',
              color: timeFrame === option.value ? '#47f8c7' : 'rgba(255,255,255,0.8)',
              fontSize: '13px',
              fontWeight: timeFrame === option.value ? 700 : 500,
              cursor: 'pointer',
              transition: 'all 0.3s',
              boxShadow: timeFrame === option.value ? '0 0 12px rgba(71, 248, 199, 0.3)' : 'none',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
            onMouseEnter={(e) => {
              if (timeFrame !== option.value) {
                e.currentTarget.style.background = 'rgba(71, 248, 199, 0.15)';
                e.currentTarget.style.borderColor = 'rgba(71, 248, 199, 0.5)';
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 4px 8px rgba(71, 248, 199, 0.2)';
              }
            }}
            onMouseLeave={(e) => {
              if (timeFrame !== option.value) {
                e.currentTarget.style.background = 'rgba(71, 248, 199, 0.08)';
                e.currentTarget.style.borderColor = 'rgba(71, 248, 199, 0.3)';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }
            }}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default RecentAnalysesCard;
