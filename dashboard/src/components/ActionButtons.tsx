import React, { useState, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { FiEdit, FiBarChart2, FiBook, FiX, FiLoader } from 'react-icons/fi';
import SpotlightCard from './SpotlightCard';
import GlassIcons from './GlassIcons';
import type { GlassIconsItem } from './GlassIcons';
import { fetchPrompt, savePrompt, triggerAnalysis } from '../api';

// ─── Prompt Modal ─────────────────────────────────────────────────────────────
const PromptModal: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [promptText, setPromptText] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'success' | 'error' | null>(null);

  useEffect(() => {
    fetchPrompt()
      .then((res) => { setPromptText(res.prompt); setLoading(false); })
      .catch(() => { setError('Failed to load prompt'); setLoading(false); });
  }, []);

  // Escape key to close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const handleSave = async () => {
    if (saving || !promptText.trim()) return;
    setSaving(true);
    setSaveStatus(null);
    try {
      await savePrompt(promptText);
      setSaveStatus('success');
    } catch {
      setSaveStatus('error');
    } finally {
      setSaving(false);
      setTimeout(() => setSaveStatus(null), 3000);
    }
  };

  const saveLabel = saving
    ? 'Saving…'
    : saveStatus === 'success'
    ? '✓ Saved!'
    : saveStatus === 'error'
    ? '✗ Error'
    : 'Save';

  const saveBg = saveStatus === 'success'
    ? 'rgba(71,248,199,0.25)'
    : saveStatus === 'error'
    ? 'rgba(224,108,117,0.25)'
    : 'rgba(71,248,199,0.12)';

  const saveBorder = saveStatus === 'success'
    ? '1px solid rgba(71,248,199,0.6)'
    : saveStatus === 'error'
    ? '1px solid rgba(224,108,117,0.5)'
    : '1px solid rgba(71,248,199,0.3)';

  return createPortal(
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        backgroundColor: 'rgba(0,0,0,0.6)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        animation: 'actionFadeIn 0.2s ease-out',
      }}
    >
      <style>{`
        @keyframes actionFadeIn  { from { opacity: 0; } to { opacity: 1; } }
        @keyframes actionScaleIn { from { opacity: 0; transform: scale(0.93); } to { opacity: 1; transform: scale(1); } }
        .prompt-textarea { resize: none; outline: none; }
        .prompt-textarea::-webkit-scrollbar { width: 6px; }
        .prompt-textarea::-webkit-scrollbar-track { background: rgba(255,255,255,0.04); border-radius: 3px; }
        .prompt-textarea::-webkit-scrollbar-thumb { background: rgba(71,248,199,0.25); border-radius: 3px; }
        .prompt-textarea::-webkit-scrollbar-thumb:hover { background: rgba(71,248,199,0.45); }
      `}</style>

      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '80vw', maxWidth: '1000px',
          height: '78vh', maxHeight: '700px',
          background: 'rgba(8, 18, 34, 0.82)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          border: '1px solid rgba(71, 248, 199, 0.2)',
          borderRadius: '20px',
          boxShadow: '0 8px 60px rgba(0,0,0,0.55), 0 0 40px rgba(71,248,199,0.07)',
          display: 'flex', flexDirection: 'column',
          animation: 'actionScaleIn 0.28s ease-out',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '20px 24px 16px',
          borderBottom: '1px solid rgba(71, 248, 199, 0.1)',
          flexShrink: 0,
        }}>
          <div>
            <h2 style={{ color: '#47f8c7', margin: '0 0 3px 0', fontSize: '18px', fontWeight: 700 }}>
              AI Analysis Prompt
            </h2>
            <p style={{ color: 'rgba(255,255,255,0.35)', margin: 0, fontSize: '11px', letterSpacing: '0.4px' }}>
              TARS · pipeline/ai_analyzer.py · build_analysis_prompt() — use {'{{TICKET_COUNT}}'}, {'{{ALL_TICKET_IDS}}'}, {'{{TICKETS_FORMATTED}}'} as placeholders
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
            {/* Save button */}
            {!loading && !error && (
              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  padding: '7px 18px',
                  borderRadius: '8px',
                  border: saveBorder,
                  background: saveBg,
                  color: saveStatus === 'error' ? '#e06c75' : '#47f8c7',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: saving ? 'wait' : 'pointer',
                  transition: 'all 0.2s',
                  letterSpacing: '0.3px',
                }}
              >
                {saveLabel}
              </button>
            )}
            {/* Close button */}
            <button
              onClick={onClose}
              style={{
                width: '32px', height: '32px', borderRadius: '50%',
                border: '1px solid rgba(71,248,199,0.3)',
                background: 'rgba(71,248,199,0.08)',
                color: 'rgba(255,255,255,0.7)',
                fontSize: '14px', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(71,248,199,0.2)';
                e.currentTarget.style.color = '#fff';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(71,248,199,0.08)';
                e.currentTarget.style.color = 'rgba(255,255,255,0.7)';
              }}
            >
              <FiX size={14} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{ flex: 1, minHeight: 0, padding: '16px 24px 24px', display: 'flex', flexDirection: 'column' }}>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, opacity: 0.5 }}>
              <div style={{
                width: '36px', height: '36px', borderRadius: '50%',
                border: '3px solid rgba(71,248,199,0.2)',
                borderTop: '3px solid #47f8c7',
                animation: 'spin 1s linear infinite',
              }} />
            </div>
          ) : error ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, opacity: 0.5 }}>
              <p style={{ color: '#e06c75', fontSize: '13px' }}>{error}</p>
            </div>
          ) : (
            <textarea
              className="prompt-textarea"
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              spellCheck={false}
              style={{
                flex: 1,
                width: '100%',
                boxSizing: 'border-box',
                padding: '16px',
                background: 'rgba(71,248,199,0.03)',
                border: '1px solid rgba(71,248,199,0.1)',
                borderRadius: '12px',
                color: 'rgba(255,255,255,0.82)',
                fontSize: '12px',
                lineHeight: '1.75',
                fontFamily: '"SF Mono", "Fira Code", "Fira Mono", monospace',
                whiteSpace: 'pre',
                overflowY: 'auto',
              }}
            />
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
};

// ─── ActionButtons ────────────────────────────────────────────────────────────
const ActionButtons: React.FC = () => {
  const [showPrompt, setShowPrompt] = useState(false);
  const [running, setRunning] = useState(false);
  const [runMsg, setRunMsg] = useState<string | null>(null);

  const handleRunAnalysis = useCallback(async () => {
    if (running) return;
    setRunning(true);
    setRunMsg(null);
    try {
      const res = await triggerAnalysis(24);
      setRunMsg(res.status === 'success' ? '✓ Done!' : '✗ Failed');
    } catch {
      setRunMsg('✗ Error');
    } finally {
      setRunning(false);
      setTimeout(() => setRunMsg(null), 4000);
    }
  }, [running]);

  const items: GlassIconsItem[] = [
    {
      icon: <FiEdit />,
      color: 'teal',
      label: 'Edit Prompt',
      onClick: () => setShowPrompt(true),
    },
    {
      icon: running ? <FiLoader style={{ animation: 'spin 1s linear infinite' }} /> : <FiBarChart2 />,
      color: running ? 'blue' : 'teal',
      label: runMsg ?? (running ? 'Running…' : 'Run Analysis'),
      onClick: handleRunAnalysis,
    },
    {
      icon: <FiBook />,
      color: 'teal',
      label: 'Last Report',
      customClass: 'glass-icon-disabled',
      onClick: () => {},
    },
  ];

  return (
    <>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .glass-icon-disabled { opacity: 0.35 !important; cursor: not-allowed !important; pointer-events: none; }
      `}</style>

      <div style={{ width: '100%' }}>
        <SpotlightCard className="custom-spotlight-card" spotlightColor="rgba(71, 248, 199, 0.2)">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <GlassIcons items={items} className="action-glass-icons" />
          </div>
        </SpotlightCard>
      </div>

      {showPrompt && <PromptModal onClose={() => setShowPrompt(false)} />}
    </>
  );
};

export default ActionButtons;
