import { useState, useRef, useCallback, useEffect } from 'react';
import { gsap } from 'gsap';
import FaultyTerminal from './components/FaultyTerminal';
import ChartsCard from './components/ChartsCard';
import KPICard from './components/KPICard';
import RecentAnalysesCard from './components/RecentAnalysesCard';
import ActionButtons from './components/ActionButtons';
import AIInsightsPanel from './components/AIInsightsPanel';
import Shuffle from './components/Shuffle';
import SplashScreen from './components/SplashScreen';
import './App.css';

function App() {
  const [showSplash, setShowSplash] = useState(true);
  const dashboardRef = useRef<HTMLDivElement>(null);

  const handleSplashComplete = useCallback(() => {
    setShowSplash(false);
  }, []);

  // Once splash is gone and dashboard mounts, fade it in
  useEffect(() => {
    if (!showSplash && dashboardRef.current) {
      gsap.fromTo(
        dashboardRef.current,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.8, ease: 'power2.out' }
      );
    }
  }, [showSplash]);

  return (
    <div style={{
      position: 'relative',
      minHeight: '100vh',
      background: 'radial-gradient(ellipse at 20% 0%, rgba(71,248,199,0.08) 0%, transparent 50%), radial-gradient(ellipse at 80% 100%, rgba(71,130,248,0.06) 0%, transparent 50%), #0A1929',
    }}>
      {/* FaultyTerminal Background — only during splash */}
      {showSplash && (
        <FaultyTerminal
          scale={1.5}
          gridMul={[2, 1]}
          digitSize={1.2}
          timeScale={0.5}
          pause={false}
          scanlineIntensity={0.5}
          glitchAmount={1}
          flickerAmount={1}
          noiseAmp={1}
          chromaticAberration={0}
          dither={0}
          curvature={0.1}
          tint="#47f8c7"
          mouseReact
          mouseStrength={0.5}
          pageLoadAnimation
          brightness={0.6}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            zIndex: 0,
          }}
        />
      )}

      {/* ── Splash Screen ── */}
      {showSplash && <SplashScreen onComplete={handleSplashComplete} />}

      {/* ── Dashboard Content — always in DOM, hidden until splash ends ── */}
      <div
        ref={dashboardRef}
        style={{
          position: 'relative',
          zIndex: showSplash ? -1 : 1,
          height: '100vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          opacity: 0,
          visibility: showSplash ? 'hidden' : 'visible',
          pointerEvents: showSplash ? 'none' : 'auto',
        }}
      >
          {/* Header */}
          <header style={{ padding: '20px 24px', flexShrink: 0 }}>
            <Shuffle
              text="TARS Dashboard"
              tag="h1"
              shuffleDirection="right"
              duration={0.35}
              animationMode="evenodd"
              shuffleTimes={1}
              ease="power3.out"
              stagger={0.03}
              threshold={0.1}
              triggerOnce={true}
              triggerOnHover
              respectReducedMotion={true}
              loop={false}
              loopDelay={0}
              textAlign="left"
              style={{ fontSize: '2rem', fontWeight: 700, color: 'white', margin: 0 }}
            />
          </header>

          {/* Bento Grid */}
          <div style={{ padding: '0 24px 24px', flex: 1, minHeight: 0, overflow: 'visible' }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr 2fr',
                gridTemplateRows: 'auto 1fr',
                gap: '16px',
                height: '100%'
              }}
            >
              {/* Top Row */}
              <div style={{ gridColumn: '1', gridRow: '1', position: 'relative' }}>
                <KPICard />
              </div>
              <div style={{ gridColumn: '2', gridRow: '1', position: 'relative' }}>
                <ActionButtons />
              </div>

              {/* Right Column — Charts on top, AI Insights below */}
              <div style={{ gridColumn: '3', gridRow: '1 / 3', display: 'flex', flexDirection: 'column', gap: '12px', overflow: 'visible', position: 'relative' }}>
                <div style={{ height: '55%', position: 'relative', overflow: 'visible', flexShrink: 0 }}>
                  <ChartsCard />
                </div>
                <div style={{ flex: 1, minHeight: 0, overflow: 'visible' }}>
                  <AIInsightsPanel />
                </div>
              </div>

              {/* Bottom Row — Recent Analyses spans cols 1-2 */}
              <div style={{ gridColumn: '1 / 3', gridRow: '2', position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                <RecentAnalysesCard />
              </div>
            </div>
          </div>
      </div>
    </div>
  );
}

export default App;
