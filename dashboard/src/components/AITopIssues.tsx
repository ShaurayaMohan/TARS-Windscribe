import React from 'react';
import SpotlightCard from './SpotlightCard';

const mockIssues = [
  { id: 1, label: 'Billing Issues', count: 89, trend: '+12%' },
  { id: 2, label: 'Authentication Errors', count: 67, trend: '-5%' },
  { id: 3, label: 'Performance Degradation', count: 54, trend: '+23%' },
  { id: 4, label: 'Account Access', count: 32, trend: '+8%' }
];

const AITopIssues: React.FC = () => {
  return (
    <div style={{ width: '100%', height: '100%' }}>
      <SpotlightCard className="custom-spotlight-card" spotlightColor="rgba(71, 248, 199, 0.2)">
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <h3 style={{ color: '#47f8c7', margin: '0 0 20px 0', fontSize: '18px', fontWeight: 600 }}>
            AI Top Issues
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
            {mockIssues.map((issue) => (
              <div
                key={issue.id}
                style={{
                  padding: '12px',
                  background: 'rgba(71, 248, 199, 0.05)',
                  borderRadius: '8px',
                  border: '1px solid rgba(71, 248, 199, 0.1)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ color: 'rgba(255,255,255,0.9)', fontSize: '14px', fontWeight: 500 }}>
                    {issue.label}
                  </span>
                  <span style={{ color: '#47f8c7', fontSize: '16px', fontWeight: 600 }}>
                    {issue.count}
                  </span>
                </div>
                <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '12px' }}>
                  {issue.trend} from last period
                </span>
              </div>
            ))}
          </div>
        </div>
      </SpotlightCard>
    </div>
  );
};

export default AITopIssues;
