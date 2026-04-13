import type { SentimentResponse } from '../api';
import {
  HiOutlineChartBar,
  HiOutlineFaceSmile,
  HiOutlineFaceFrown,
  HiOutlineExclamationTriangle,
} from 'react-icons/hi2';

interface Props {
  data: SentimentResponse | null;
  loading: boolean;
}

export default function SentimentStats({ data, loading }: Props) {
  const total = data?.total_scored ?? 0;
  const positive = data?.sentiment?.positive ?? 0;
  const frustrated = (data?.sentiment?.frustrated ?? 0) + (data?.sentiment?.angry ?? 0);
  const highChurn = data?.churn_risk?.high ?? 0;
  const positivePct = total > 0 ? Math.round((positive / total) * 100) : 0;
  const negPct = total > 0 ? Math.round((frustrated / total) * 100) : 0;

  const cards = [
    { label: 'Total Scored', display: String(total), color: '#00d09c', icon: HiOutlineChartBar },
    { label: 'Positive', display: `${positivePct}%`, color: '#22c55e', icon: HiOutlineFaceSmile },
    { label: 'Frustrated + Angry', display: `${negPct}%`, color: '#f59e0b', icon: HiOutlineFaceFrown },
    { label: 'High Churn', display: String(highChurn), color: '#ef4444', icon: HiOutlineExclamationTriangle },
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
              <div className="h-9 w-16 rounded bg-ws-border/50 animate-pulse" />
            ) : (
              <p
                className="text-3xl font-mono font-bold tracking-tight"
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
