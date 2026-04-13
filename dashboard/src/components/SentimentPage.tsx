import { useState, useEffect, useCallback } from 'react';
import type { SentimentResponse, SentimentTicket, DateRange } from '../api';
import { fetchSentiment, fetchSentimentTickets } from '../api';
import HealthScore from './HealthScore';
import SentimentStats from './SentimentStats';
import SentimentCharts from './SentimentCharts';
import DateRangeFilter from './DateRangeFilter';
import SentimentTable from './SentimentTable';

export default function SentimentPage() {
  const [data, setData] = useState<SentimentResponse | null>(null);
  const [tickets, setTickets] = useState<SentimentTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [ticketsLoading, setTicketsLoading] = useState(true);
  const [sentimentFilter, setSentimentFilter] = useState('');
  const [urgencyFilter, setUrgencyFilter] = useState('');
  const [churnFilter, setChurnFilter] = useState('');
  const [dateRange, setDateRange] = useState<DateRange>({});

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const range = dateRange.fromDate || dateRange.toDate ? dateRange : undefined;
      const res = await fetchSentiment(30, range);
      setData(res);
    } catch (err) {
      console.error('Failed to fetch sentiment:', err);
    } finally {
      setLoading(false);
    }
  }, [dateRange]);

  const loadTickets = useCallback(async () => {
    setTicketsLoading(true);
    try {
      const range = dateRange.fromDate || dateRange.toDate ? dateRange : undefined;
      const res = await fetchSentimentTickets(
        30,
        sentimentFilter || undefined,
        urgencyFilter || undefined,
        churnFilter || undefined,
        range,
      );
      setTickets(res.tickets);
    } catch (err) {
      console.error('Failed to fetch sentiment tickets:', err);
    } finally {
      setTicketsLoading(false);
    }
  }, [dateRange, sentimentFilter, urgencyFilter, churnFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    loadTickets();
  }, [loadTickets]);

  function handleDateApply(from: string, to: string) {
    setDateRange({ fromDate: from || undefined, toDate: to || undefined });
  }

  function handleDateClear() {
    setDateRange({});
  }

  return (
    <div className="space-y-6">
      <HealthScore data={data} loading={loading} />
      <SentimentStats data={data} loading={loading} />
      <SentimentCharts data={data} loading={loading} />
      <div className="glass-card rounded-xl p-4 animate-fade-in" style={{ animationDelay: '300ms' }}>
        <DateRangeFilter
          onApply={handleDateApply}
          onClear={handleDateClear}
          hasActiveFilter={!!(dateRange.fromDate || dateRange.toDate)}
        />
      </div>
      <SentimentTable
        tickets={tickets}
        loading={ticketsLoading}
        sentimentFilter={sentimentFilter}
        urgencyFilter={urgencyFilter}
        churnFilter={churnFilter}
        onSentimentChange={setSentimentFilter}
        onUrgencyChange={setUrgencyFilter}
        onChurnChange={setChurnFilter}
      />
    </div>
  );
}
