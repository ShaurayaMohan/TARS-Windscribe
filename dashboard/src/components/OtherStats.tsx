import React from 'react';
import SpotlightCard from './SpotlightCard';

interface OtherStatsProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactElement;
}

const OtherStats: React.FC<OtherStatsProps> = ({ title, value, subtitle, icon }) => {
  return (
    <div style={{ width: '100%', height: '100%' }}>
      <SpotlightCard className="custom-spotlight-card" spotlightColor="rgba(71, 248, 199, 0.2)">
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'center' }}>
          {icon && (
            <div style={{ marginBottom: '12px', color: '#47f8c7' }}>
              {icon}
            </div>
          )}
          <h3 style={{ color: '#47f8c7', margin: '0 0 8px 0', fontSize: '14px', fontWeight: 600 }}>
            {title}
          </h3>
          <div style={{ color: 'rgba(255,255,255,0.9)', fontSize: '24px', fontWeight: 700, marginBottom: '4px' }}>
            {value}
          </div>
          {subtitle && (
            <p style={{ color: 'rgba(255,255,255,0.6)', margin: 0, fontSize: '12px' }}>
              {subtitle}
            </p>
          )}
        </div>
      </SpotlightCard>
    </div>
  );
};

export default OtherStats;
