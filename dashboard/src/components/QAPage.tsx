import { useState, useEffect, useCallback } from 'react';
import type { QAStatsResponse, QATicket, DateRange } from '../api';
import { fetchQAStats, fetchQATickets } from '../api';
import StatsCards from './StatsCards';
import DateRangeFilter from './DateRangeFilter';
import TicketTable from './TicketTable';

export default function QAPage() {
  const [stats, setStats] = useState<QAStatsResponse | null>(null);
  const [tickets, setTickets] = useState<QATicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [platform, setPlatform] = useState('');
  const [status, setStatus] = useState('');
  const [dateRange, setDateRange] = useState<DateRange>({});

  const range = dateRange.fromDate || dateRange.toDate ? dateRange : undefined;

  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const data = await fetchQAStats(30, range);
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    } finally {
      setStatsLoading(false);
    }
  }, [range]);

  const loadTickets = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchQATickets(30, platform || undefined, status || undefined, range);
      setTickets(data.tickets);
    } catch (err) {
      console.error('Failed to fetch tickets:', err);
    } finally {
      setLoading(false);
    }
  }, [range, platform, status]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    loadTickets();
  }, [loadTickets]);

  function handleDateApply(from: string, to: string) {
    setDateRange({ fromDate: from || undefined, toDate: to || undefined });
  }

  function handleDateClear() {
    setDateRange({});
  }

  function handleTicketUpdated() {
    loadStats();
    loadTickets();
  }

  function handleTicketDismissed(ticketId: string) {
    setTickets((prev) => prev.filter((t) => t._id !== ticketId));
    loadStats();
  }

  return (
    <div className="space-y-6">
      <StatsCards stats={stats} loading={statsLoading} />
      <div className="glass-card rounded-xl p-4 animate-fade-in" style={{ animationDelay: '300ms' }}>
        <DateRangeFilter
          onApply={handleDateApply}
          onClear={handleDateClear}
          hasActiveFilter={!!(dateRange.fromDate || dateRange.toDate)}
        />
      </div>
      <TicketTable
        tickets={tickets}
        loading={loading}
        platformFilter={platform}
        statusFilter={status}
        onPlatformChange={setPlatform}
        onStatusChange={setStatus}
        onTicketUpdated={handleTicketUpdated}
        onTicketDismissed={handleTicketDismissed}
      />
    </div>
  );
}
