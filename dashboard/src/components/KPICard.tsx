import React, { useEffect, useState } from 'react';
import Carousel from './Carousel';
import { FiBarChart2, FiAlertTriangle, FiMapPin, FiRefreshCw } from 'react-icons/fi';
import { fetchStats, timeAgo, type StatsResponse } from '../api';

interface CarouselItem {
  title: string;
  description: string;
  id: number;
  icon: React.ReactElement;
}

function buildKpiItems(stats: StatsResponse): CarouselItem[] {
  const latest = stats.latest_analysis;
  const topCat = latest?.top_category ?? null;

  return [
    {
      id: 1,
      title: 'Tickets Analyzed (7d)',
      description: stats.last_7_days_tickets > 0
        ? stats.last_7_days_tickets.toLocaleString() + ' tickets'
        : 'No data',
      icon: <FiBarChart2 className="carousel-icon" />,
    },
    {
      id: 2,
      title: 'Last Analysis Run',
      description: latest?.date ? timeAgo(latest.date) : 'Never',
      icon: <FiRefreshCw className="carousel-icon" />,
    },
    {
      id: 3,
      title: 'Top Issue (Latest)',
      description: topCat?.title ?? '—',
      icon: <FiAlertTriangle className="carousel-icon" />,
    },
    {
      id: 4,
      title: 'Top Issue Volume',
      description: topCat ? `${topCat.count} tickets` : 'N/A',
      icon: <FiMapPin className="carousel-icon" />,
    },
  ];
}

const loadingItems: CarouselItem[] = [
  { id: 1, title: 'Tickets Analyzed (7d)', description: '…', icon: <FiBarChart2 className="carousel-icon" /> },
  { id: 2, title: 'Last Analysis Run',     description: '…', icon: <FiRefreshCw className="carousel-icon" /> },
  { id: 3, title: 'Top Issue (Latest)',    description: '…', icon: <FiAlertTriangle className="carousel-icon" /> },
  { id: 4, title: 'Top Issue Volume',      description: '…', icon: <FiMapPin className="carousel-icon" /> },
];

const KPICard: React.FC = () => {
  const [items, setItems] = useState<CarouselItem[]>(loadingItems);

  useEffect(() => {
    let cancelled = false;

    fetchStats()
      .then((stats) => {
        if (!cancelled) setItems(buildKpiItems(stats));
      })
      .catch(() => {
        if (!cancelled) {
          setItems(buildKpiItems({
            latest_analysis: null,
            today_analyses: 0,
            total_analyses: 0,
            last_7_days_tickets: 0,
          }));
        }
      });

    return () => { cancelled = true; };
  }, []);

  return (
    <div style={{ width: '100%', position: 'relative' }}>
      <Carousel
        items={items}
        baseWidth={300}
        autoplay={true}
        autoplayDelay={4000}
        pauseOnHover={true}
        loop={true}
        round={false}
      />
    </div>
  );
};

export default KPICard;
