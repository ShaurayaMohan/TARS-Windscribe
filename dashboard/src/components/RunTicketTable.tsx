import { useState } from 'react';
import type { Ticket } from '../api';
import { ticketUrl } from '../api';
import { HiOutlineArrowTopRightOnSquare } from 'react-icons/hi2';
import Pagination from './Pagination';

interface Props {
  tickets: Ticket[];
  loading: boolean;
}

const PER_PAGE = 10;

function statusColor(status: string): string {
  const s = status.toLowerCase();
  if (s === 'open' || s === 'active') return '#22c55e';
  if (s === 'pending') return '#f59e0b';
  return '#9ca3af';
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max) + '\u2026';
}

export default function RunTicketTable({ tickets, loading }: Props) {
  const [page, setPage] = useState(1);
  const totalPages = Math.ceil(tickets.length / PER_PAGE);
  const paged = tickets.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  return (
    <div className="glass-card rounded-xl overflow-hidden animate-fade-in" style={{ animationDelay: '160ms' }}>
      <div className="px-6 py-4 border-b border-ws-border/40">
        <h3 className="font-mono text-[11px] uppercase tracking-wider text-ws-muted">
          Tickets from this run <span className="text-ws-text">({tickets.length})</span>
        </h3>
      </div>
      <div className="overflow-x-auto">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3 text-ws-muted">
              <div className="w-5 h-5 border-2 border-ws-green/30 border-t-ws-green rounded-full animate-spin" />
              <span className="font-mono text-sm">Loading tickets...</span>
            </div>
          </div>
        ) : tickets.length === 0 ? (
          <div className="flex items-center justify-center py-20 text-ws-muted">
            <p className="font-mono text-sm">No tickets found for this run.</p>
          </div>
        ) : (
          <table className="w-full text-base">
            <thead>
              <tr className="border-b border-ws-border bg-white/[0.02] text-ws-muted text-left">
                <th className="px-4 py-3.5 font-mono text-xs uppercase tracking-wider font-medium">Ticket #</th>
                <th className="px-4 py-3.5 font-mono text-xs uppercase tracking-wider font-medium">AI Summary</th>
                <th className="px-4 py-3.5 font-mono text-xs uppercase tracking-wider font-medium">Category</th>
                <th className="px-4 py-3.5 font-mono text-xs uppercase tracking-wider font-medium">Status</th>
                <th className="px-4 py-3.5 w-12"></th>
              </tr>
            </thead>
            <tbody>
              {paged.map((ticket) => (
                <tr
                  key={ticket._id}
                  className="border-b border-ws-border/40 hover:bg-ws-green/[0.03] transition-colors"
                >
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    <a
                      href={ticketUrl(ticket.supportpal_id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-ws-green hover:text-ws-green-dim hover:underline underline-offset-2 transition-colors"
                    >
                      #{ticket.ticket_number}
                    </a>
                  </td>
                  <td className="px-4 py-3.5 max-w-md">
                    <p className="text-ws-text text-[15px]">
                      {truncate(ticket.ai_summary, 120)}
                    </p>
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    <span className="text-sm text-ws-muted">
                      {ticket.category_id ?? '\u2014'}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    <span
                      className="text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap"
                      style={{
                        color: statusColor(ticket.status),
                        background: `${statusColor(ticket.status)}20`,
                      }}
                    >
                      {ticket.status}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
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
  );
}
