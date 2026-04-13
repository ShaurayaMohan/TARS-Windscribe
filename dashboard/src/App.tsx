import { useState } from 'react';
import TabNav from './components/TabNav';
import DailyRunsPage from './components/DailyRunsPage';
import QAPage from './components/QAPage';
import SentimentPage from './components/SentimentPage';

type Tab = 'daily_runs' | 'qa' | 'sentiment';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('daily_runs');

  return (
    <div className="min-h-screen bg-ws-bg">
      <div className="h-[2px] bg-gradient-to-r from-transparent via-ws-green/60 to-transparent" />
      <TabNav activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'daily_runs' && <DailyRunsPage />}
        {activeTab === 'qa' && <QAPage />}
        {activeTab === 'sentiment' && <SentimentPage />}
      </main>
    </div>
  );
}
