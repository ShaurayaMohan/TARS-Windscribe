import { useState } from 'react';
import type { SentimentTicket } from '../api';
import {
  ticketUrl,
  SENTIMENT_LABELS,
  URGENCY_LABELS,
  CHURN_LABELS,
  SENTIMENT_COLORS,
  URGENCY_COLORS,
  CHURN_COLORS,
} from '../api';
import { HiOutlineFunnel, HiOutlineArrowTopRightOnSquare } from 'react-icons/hi2';
import Pagination from './Pagination';

interface Props {
  tickets: SentimentTicket[];
  loading: boolean;
  sentimentFilter: string;
  urgencyFilter: string;
  churnFilter: string;
  onSentimentChange: (val: string) => void;
  onUrgencyChange: (val: string) => void;
  onChurnChange: (val: string) => void;
}

const PER_PAGE = 10;

const sentimentOptions = [
  { value: '', label: 'All Sentiment' },
  { value: 'positive', label: 'Positive' },
  { value: 'neutral_confused', label: 'Neutral / Confused' },
  { value: 'frustrated', label: 'Frustrated' },
  { value: 'angry', label: 'Angry' },
];

const urgencyOptions = [
  { value: '', label: 'All Urgency' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
];

const churnOptions = [
  { value: '', label: 'All Churn' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
];

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="text-[11px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap"
      style={{ color, background: `${color}20` }}
    >
      {label}
    </span>
  );
}

const filterConfigs = [
  (p: Props) => ({ value: p.sentimentFilter, onChange: p.onSentimentChange, options: sentimentOptions }),
  (p: Props) => ({ value: p.urgencyFilter, onChange: p.onUrgencyChange, options: urgencyOptions }),
  (p: Props) => ({ value: p.churnFilter, onChange: p.onChurnChange, options: churnOptions }),
];

export default function SentimentTable(props: Props) {
  const { tickets, loading } = props;
  const [page, setPage] = useState(1);

  const totalPages = Math.ceil(tickets.length / PER_PAGE);
  const paged = tickets.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  // Reset to page 1 when tickets change (filter)
  const ticketKey = tickets.map((t) => t._id).join(',');
  const [prevKey, setPrevKey] = useState(ticketKey);
  if (ticketKey !== prevKey) {
    setPrevKey(ticketKey);
    if (page !== 1) setPage(1);
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-3 mb-4 animate-fade-in" style={{ animationDelay: '320ms' }}>
        <HiOutlineFunnel className="w-4 h-4 text-ws-muted" />
        {filterConfigs.map((getFilter, i) => {
          const filter = getFilter(props);
          return (
            <select
              key={i}
              value={filter.value}
              onChange={(e) => filter.onChange(e.target.value)}
              className="glass-card rounded-lg px-3 py-1.5 text-sm text-ws-text bg-transparent focus:outline-none focus:border-ws-green cursor-pointer"
            >
              {filter.options.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-[#111827] text-[#e5e7eb]">
                  {opt.label}
                </option>
              ))}
            </select>
          );
        })}
      </div>

      <div className="glass-card rounded-xl overflow-hidden animate-fade-in" style={{ animationDelay: '400ms' }}>
        <div className="overflow-x-auto">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="flex items-center gap-3 text-ws-muted">
                <div className="w-5 h-5 border-2 border-ws-green/30 border-t-ws-green rounded-full animate-spin" />
                <span className="font-mono text-sm">Loading tickets...</span>
              </div>
            </div>
          ) : tickets.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-ws-muted">
              <p className="font-mono text-sm">No sentiment tickets found for this period.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ws-border bg-white/[0.02] text-ws-muted text-left">
                  <th className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider font-medium">Ticket #</th>
                  <th className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider font-medium">Summary</th>
                  <th className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider font-medium">Sentiment</th>
                  <th className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider font-medium">Urgency</th>
                  <th className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider font-medium">Churn</th>
                  <th className="px-4 py-3 w-12"></th>
                </tr>
              </thead>
              <tbody>
                {paged.map((ticket) => (
                  <tr
                    key={ticket._id}
                    className="border-b border-ws-border/40 hover:bg-ws-green/[0.03] transition-colors"
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <a
                        href={ticketUrl(ticket.supportpal_id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-ws-green hover:text-ws-green-dim hover:underline underline-offset-2 transition-colors"
                      >
                        #{ticket.ticket_number}
                      </a>
                    </td>
                    <td className="px-4 py-3 max-w-sm">
                      <p className="text-ws-text text-[13px] truncate">
                        {ticket.sentiment_summary}
                      </p>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Badge
                        label={SENTIMENT_LABELS[ticket.sentiment] || ticket.sentiment}
                        color={SENTIMENT_COLORS[ticket.sentiment] || '#6b7280'}
                      />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Badge
                        label={URGENCY_LABELS[ticket.urgency] || ticket.urgency}
                        color={URGENCY_COLORS[ticket.urgency] || '#6b7280'}
                      />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Badge
                        label={CHURN_LABELS[ticket.churn_risk] || ticket.churn_risk}
                        color={CHURN_COLORS[ticket.churn_risk] || '#6b7280'}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <a
                        href={ticketUrl(ticket.supportpal_id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 rounded-lg text-ws-muted hover:text-ws-green hover:bg-ws-green/10 transition-colors inline-flex"
                      >
                        <HiOutlineArrowTopRightOnSquare className="w-4 h-4" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        {!loading && tickets.length > 0 && (
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        )}
      </div>
    </>
  );
}
