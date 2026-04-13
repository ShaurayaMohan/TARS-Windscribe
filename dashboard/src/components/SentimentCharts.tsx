import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import type { SentimentResponse } from '../api';
import {
  SENTIMENT_LABELS,
  URGENCY_LABELS,
  CHURN_LABELS,
  SENTIMENT_COLORS,
  URGENCY_COLORS,
  CHURN_COLORS,
} from '../api';

interface Props {
  data: SentimentResponse | null;
  loading: boolean;
}

interface ChartConfig {
  title: string;
  dataKey: 'sentiment' | 'urgency' | 'churn_risk';
  labels: Record<string, string>;
  colors: Record<string, string>;
}

const charts: ChartConfig[] = [
  { title: 'Sentiment', dataKey: 'sentiment', labels: SENTIMENT_LABELS, colors: SENTIMENT_COLORS },
  { title: 'Urgency', dataKey: 'urgency', labels: URGENCY_LABELS, colors: URGENCY_COLORS },
  { title: 'Churn Risk', dataKey: 'churn_risk', labels: CHURN_LABELS, colors: CHURN_COLORS },
];

export default function SentimentCharts({ data, loading }: Props) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="glass-card rounded-xl p-6 animate-fade-in"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className="h-52 flex items-center justify-center">
              <div className="w-36 h-36 rounded-full bg-ws-border/30 animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {charts.map((chart, i) => {
        const rawData = data[chart.dataKey] as Record<string, number>;
        const entries = Object.entries(rawData).filter(([, v]) => v > 0);
        const pieData = entries.map(([key, value]) => ({
          name: chart.labels[key] || key,
          value,
          color: chart.colors[key] || '#6b7280',
        }));
        const total = pieData.reduce((sum, d) => sum + d.value, 0);

        return (
          <div
            key={chart.dataKey}
            className="glass-card rounded-xl p-6 animate-fade-in"
            style={{ animationDelay: `${i * 100}ms` }}
          >
            <h3 className="font-mono text-[11px] uppercase tracking-wider text-ws-muted text-center mb-3">
              {chart.title}
            </h3>
            {pieData.length === 0 ? (
              <div className="h-48 flex items-center justify-center text-ws-muted text-sm font-mono">
                No data
              </div>
            ) : (
              <>
                <div className="relative">
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={78}
                        paddingAngle={2}
                        dataKey="value"
                        stroke="none"
                        animationBegin={i * 150}
                        animationDuration={800}
                      >
                        {pieData.map((entry, idx) => (
                          <Cell key={idx} fill={entry.color} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <span className="font-mono text-lg font-bold text-ws-text">{total}</span>
                  </div>
                </div>
                <div className="flex flex-wrap justify-center gap-x-4 gap-y-1.5 mt-1">
                  {pieData.map((entry) => (
                    <div key={entry.name} className="flex items-center gap-1.5 text-xs">
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: entry.color }}
                      />
                      <span className="text-ws-muted">
                        {entry.name}:{' '}
                        <span className="text-ws-text font-medium">{entry.value}</span>
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
