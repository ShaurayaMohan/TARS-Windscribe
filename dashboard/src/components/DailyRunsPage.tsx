import { useState, useEffect, useCallback } from 'react';
import type { StatsResponse, Analysis, Ticket } from '../api';
import { fetchStats, fetchAnalyses, fetchAnalysisTickets } from '../api';
import RunStatsCards from './RunStatsCards';
import RunSelector from './RunSelector';
import RunDetail from './RunDetail';
import RunTicketTable from './RunTicketTable';

export default function DailyRunsPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);
  const [analysesLoading, setAnalysesLoading] = useState(true);
  const [ticketsLoading, setTicketsLoading] = useState(false);

  const loadAll = useCallback(async () => {
    setStatsLoading(true);
    setAnalysesLoading(true);
    try {
      const [statsRes, analysesRes] = await Promise.all([
        fetchStats(),
        fetchAnalyses(50),
      ]);
      setStats(statsRes);
      setAnalyses(analysesRes.analyses);
      if (analysesRes.analyses.length > 0) {
        setSelectedId((prev) => prev || analysesRes.analyses[0]._id);
      }
    } catch (err) {
      console.error('Failed to fetch daily runs data:', err);
    } finally {
      setStatsLoading(false);
      setAnalysesLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (!selectedId) {
      setTickets([]);
      return;
    }
    setTicketsLoading(true);
    fetchAnalysisTickets(selectedId)
      .then((res) => setTickets(res.tickets))
      .catch((err) => console.error('Failed to fetch tickets:', err))
      .finally(() => setTicketsLoading(false));
  }, [selectedId]);

  const selectedAnalysis = analyses.find((a) => a._id === selectedId) ?? null;

  return (
    <div className="space-y-6">
      <RunStatsCards stats={stats} loading={statsLoading} />
      <div className="glass-card rounded-xl p-4 animate-fade-in" style={{ animationDelay: '320ms' }}>
        <RunSelector
          analyses={analyses}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onRunComplete={loadAll}
        />
      </div>
      {analysesLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3 text-ws-muted">
            <div className="w-5 h-5 border-2 border-ws-green/30 border-t-ws-green rounded-full animate-spin" />
            <span className="font-mono text-sm">Loading runs...</span>
          </div>
        </div>
      ) : analyses.length === 0 ? (
        <div className="glass-card rounded-xl p-12 text-center animate-fade-in">
          <p className="font-mono text-sm text-ws-muted">
            No analysis runs yet. Click "Run Analysis Now" to start.
          </p>
        </div>
      ) : (
        <>
          <RunDetail analysis={selectedAnalysis} loading={ticketsLoading && !selectedAnalysis} />
          <RunTicketTable tickets={tickets} loading={ticketsLoading} />
        </>
      )}
    </div>
  );
}
