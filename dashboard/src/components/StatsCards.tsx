import type { QAStatsResponse } from '../api';
import {
  HiOutlineBugAnt,
  HiOutlineQuestionMarkCircle,
  HiOutlineExclamationTriangle,
  HiOutlineArrowTrendingUp,
} from 'react-icons/hi2';

interface Props {
  stats: QAStatsResponse | null;
  loading: boolean;
}

const cards = [
  { key: 'total_bugs' as const, label: 'Total Bugs', color: '#00d09c', icon: HiOutlineBugAnt },
  { key: 'not_tested' as const, label: 'Not Tested', color: '#6b7280', icon: HiOutlineQuestionMarkCircle },
  { key: 'reproduced' as const, label: 'Reproduced', color: '#f59e0b', icon: HiOutlineExclamationTriangle },
  { key: 'escalated' as const, label: 'Escalated', color: '#ef4444', icon: HiOutlineArrowTrendingUp },
];

export default function StatsCards({ stats, loading }: Props) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, i) => {
        const Icon = card.icon;
        const value = stats ? stats[card.key] : 0;
        return (
          <div
            key={card.key}
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
                style={{
                  color: card.color,
                  background: `${card.color}15`,
                }}
              >
                {card.label}
              </span>
            </div>
            {loading ? (
              <div className="h-9 w-16 rounded bg-ws-border/50 animate-pulse" />
            ) : (
              <p
                className="text-3xl font-mono font-bold tracking-tight"
                style={{ color: card.color }}
              >
                {value}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
