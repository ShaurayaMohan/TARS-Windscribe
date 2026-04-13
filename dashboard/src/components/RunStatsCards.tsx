import type { StatsResponse } from '../api';
import {
  HiOutlinePlayCircle,
  HiOutlineClock,
  HiOutlineTicket,
  HiOutlineCalendarDays,
} from 'react-icons/hi2';

interface Props {
  stats: StatsResponse | null;
  loading: boolean;
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'No runs yet';
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export default function RunStatsCards({ stats, loading }: Props) {
  const cards = [
    {
      label: 'Total Runs',
      display: String(stats?.total_analyses ?? 0),
      color: '#00d09c',
      icon: HiOutlinePlayCircle,
    },
    {
      label: "Today's Runs",
      display: String(stats?.today_analyses ?? 0),
      color: '#0ecb81',
      icon: HiOutlineClock,
    },
    {
      label: '7-Day Tickets',
      display: String(stats?.last_7_days_tickets ?? 0),
      color: '#f59e0b',
      icon: HiOutlineTicket,
    },
    {
      label: 'Latest Run',
      display: formatDate(stats?.latest_analysis?.date),
      color: '#9ca3af',
      icon: HiOutlineCalendarDays,
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, i) => {
        const Icon = card.icon;
        return (
          <div
            key={card.label}
            className="glass-card rounded-xl p-5 animate-fade-in group transition-all duration-300"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className="flex items-center justify-between mb-3">
              <Icon
                className="w-5 h-5 opacity-40 group-hover:opacity-80 transition-opacity"
                style={{ color: card.color }}
              />
              <span
                className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full"
                style={{ color: card.color, background: `${card.color}15` }}
              >
                {card.label}
              </span>
            </div>
            {loading ? (
              <div className="h-9 w-20 rounded bg-ws-border/50 animate-pulse" />
            ) : (
              <p
                className="text-2xl font-mono font-bold tracking-tight"
                style={{ color: card.color }}
              >
                {card.display}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
