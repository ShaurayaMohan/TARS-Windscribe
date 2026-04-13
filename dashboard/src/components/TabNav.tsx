type Tab = 'daily_runs' | 'qa' | 'sentiment';

interface Props {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
}

const tabs: { id: Tab; label: string }[] = [
  { id: 'daily_runs', label: 'Daily Runs' },
  { id: 'qa', label: 'QA' },
  { id: 'sentiment', label: 'Sentiment' },
];

export default function TabNav({ activeTab, onTabChange }: Props) {
  return (
    <nav className="glass-card border-t-0 border-x-0 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-14">
        <div className="flex items-center gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`px-4 py-2 text-sm font-medium transition-all duration-200 relative cursor-pointer ${
                activeTab === tab.id
                  ? 'text-ws-green'
                  : 'text-ws-muted hover:text-ws-text'
              }`}
            >
              {tab.label}
              {activeTab === tab.id && (
                <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-ws-green rounded-full" />
              )}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <span
            className="text-[10px] text-ws-muted tracking-widest"
            style={{ fontFamily: "'Press Start 2P', monospace" }}
          >
            T.A.R.S
          </span>
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ws-green opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-ws-green" />
          </span>
        </div>
      </div>
    </nav>
  );
}
