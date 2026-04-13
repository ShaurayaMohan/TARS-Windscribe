import { useState } from 'react';
import type { QATicket, QAStatus } from '../api';
import {
  updateQATicketStatus,
  dismissQATicket,
  ticketUrl,
  PLATFORM_LABELS,
  FEATURE_AREA_LABELS,
} from '../api';
import { HiOutlineTrash, HiOutlineFunnel } from 'react-icons/hi2';
import DismissModal from './DismissModal';
import Pagination from './Pagination';

interface Props {
  tickets: QATicket[];
  loading: boolean;
  platformFilter: string;
  statusFilter: string;
  onPlatformChange: (platform: string) => void;
  onStatusChange: (status: string) => void;
  onTicketUpdated: () => void;
  onTicketDismissed: (ticketId: string) => void;
}

const PER_PAGE = 10;

const STATUS_COLORS: Record<QAStatus, string> = {
  not_tested: '#6b7280',
  reproduced: '#f59e0b',
  escalated: '#ef4444',
};

const STATUS_LABELS: Record<QAStatus, string> = {
  not_tested: 'Not Tested',
  reproduced: 'Reproduced',
  escalated: 'Escalated',
};

const platforms = [
  { value: '', label: 'All Platforms' },
  { value: 'windows', label: 'Windows' },
  { value: 'macos', label: 'macOS' },
  { value: 'linux', label: 'Linux' },
  { value: 'android', label: 'Android' },
  { value: 'ios', label: 'iOS' },
  { value: 'router', label: 'Router' },
  { value: 'browser_extension', label: 'Browser Ext' },
  { value: 'tv', label: 'TV' },
];

const statusFilters = [
  { value: '', label: 'All' },
  { value: 'not_tested', label: 'NT' },
  { value: 'reproduced', label: 'R' },
  { value: 'escalated', label: 'E' },
];

export default function TicketTable({
  tickets,
  loading,
  platformFilter,
  statusFilter,
  onPlatformChange,
  onStatusChange,
  onTicketUpdated,
  onTicketDismissed,
}: Props) {
  const [dismissTarget, setDismissTarget] = useState<QATicket | null>(null);
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set());
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

  async function handleStatusChange(ticket: QATicket, newStatus: QAStatus) {
    if (newStatus === ticket.qa_status) return;
    setUpdatingIds((prev) => new Set(prev).add(ticket._id));
    try {
      await updateQATicketStatus(ticket._id, newStatus);
      onTicketUpdated();
    } catch (err) {
      console.error('Failed to update status:', err);
    } finally {
      setUpdatingIds((prev) => {
        const next = new Set(prev);
        next.delete(ticket._id);
        return next;
      });
    }
  }

  async function handleDismiss(ticket: QATicket) {
    try {
      await dismissQATicket(ticket._id);
      onTicketDismissed(ticket._id);
    } catch (err) {
      console.error('Failed to dismiss:', err);
    }
    setDismissTarget(null);
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-4 mb-4 animate-fade-in" style={{ animationDelay: '320ms' }}>
        <div className="flex items-center gap-2">
          <HiOutlineFunnel className="w-4 h-4 text-ws-muted" />
          <select
            value={platformFilter}
            onChange={(e) => onPlatformChange(e.target.value)}
            className="glass-card rounded-lg px-3 py-1.5 text-sm text-ws-text bg-transparent focus:outline-none focus:border-ws-green cursor-pointer"
          >
            {platforms.map((p) => (
              <option key={p.value} value={p.value} className="bg-[#111827] text-ws-text">
                {p.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-1">
          {statusFilters.map((s) => (
            <button
              key={s.value}
              onClick={() => onStatusChange(s.value)}
              className={`px-3 py-1.5 text-xs font-mono rounded-lg transition-all duration-200 cursor-pointer ${
                statusFilter === s.value
                  ? 'bg-ws-green/15 text-ws-green border border-ws-green/30'
                  : 'glass-card text-ws-muted hover:text-ws-text'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
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
              <p className="font-mono text-sm">No QA tickets found for this period.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ws-border bg-white/[0.02] text-ws-muted text-left">
                  <th className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider font-medium">Ticket #</th>
                  <th className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider font-medium">Description</th>
                  <th className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider font-medium">Feature</th>
                  <th className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider font-medium">Platform</th>
                  <th className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider font-medium">Status</th>
                  <th className="px-4 py-3 font-mono text-[11px] uppercase tracking-wider font-medium w-16"></th>
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
                      <p className="text-ws-text truncate text-[13px]">{ticket.subject}</p>
                      {ticket.qa_error_pattern && (
                        <p className="text-ws-muted text-xs mt-0.5 truncate opacity-70">
                          {ticket.qa_error_pattern}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-xs text-ws-muted">
                        {FEATURE_AREA_LABELS[ticket.qa_feature_area] || ticket.qa_feature_area}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-white/[0.06] text-ws-text">
                        {PLATFORM_LABELS[ticket.qa_platform] || ticket.qa_platform}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <select
                        value={ticket.qa_status}
                        onChange={(e) => handleStatusChange(ticket, e.target.value as QAStatus)}
                        disabled={updatingIds.has(ticket._id)}
                        className="text-xs font-mono px-2 py-1 rounded-md bg-transparent border cursor-pointer focus:outline-none disabled:opacity-50 transition-colors"
                        style={{
                          color: STATUS_COLORS[ticket.qa_status],
                          borderColor: `${STATUS_COLORS[ticket.qa_status]}40`,
                        }}
                      >
                        {(['not_tested', 'reproduced', 'escalated'] as QAStatus[]).map((s) => (
                          <option key={s} value={s} className="bg-[#111827] text-[#e5e7eb]">
                            {STATUS_LABELS[s]}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setDismissTarget(ticket)}
                        className="p-1.5 rounded-lg text-ws-muted hover:text-red-400 hover:bg-red-400/10 transition-colors cursor-pointer"
                        title="Dismiss ticket"
                      >
                        <HiOutlineTrash className="w-4 h-4" />
                      </button>
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

      {dismissTarget && (
        <DismissModal
          ticket={dismissTarget}
          onCancel={() => setDismissTarget(null)}
          onConfirm={() => handleDismiss(dismissTarget)}
        />
      )}
    </>
  );
}
