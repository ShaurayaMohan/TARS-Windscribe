import React, { useState, useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import TextType from './TextType';
import './SplashScreen.css';

interface SplashScreenProps {
  onComplete: () => void;
}

const SplashScreen: React.FC<SplashScreenProps> = ({ onComplete }) => {
  const [typingDone, setTypingDone] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);

  // "WELCOME TO T.A.R.S" has 19 chars. At 80ms each ≈ 1.5s typing.
  // Then we hold for ~2s, then fade out over ~1s. Total ≈ 4.5s.
  const TYPING_SPEED = 80;
  const HOLD_DURATION = 2000; // ms to hold after typing finishes

  // Once typing completes, wait, then trigger fade-out
  useEffect(() => {
    if (!typingDone) return;

    const holdTimer = setTimeout(() => {
      // Fade-out animation
      const tl = gsap.timeline({
        onComplete: () => {
          onComplete();
        },
      });

      // Scale up + fade the text first
      tl.to(textRef.current, {
        scale: 1.1,
        opacity: 0,
        duration: 0.6,
        ease: 'power2.in',
      });

      // Then fade the whole container
      tl.to(
        containerRef.current,
        {
          opacity: 0,
          duration: 0.5,
          ease: 'power2.inOut',
        },
        '-=0.2'
      );
    }, HOLD_DURATION);

    return () => clearTimeout(holdTimer);
  }, [typingDone, onComplete]);

  // Detect when the full text has been typed
  // TextType doesn't have a direct "onComplete" for the first sentence in non-loop mode,
  // so we'll use onSentenceComplete (fires after full text + no loop = stays)
  // Actually, with loop=false and a single text, it won't fire onSentenceComplete.
  // Instead we'll calculate timing manually.
  const fullText = 'WELCOME TO T.A.R.S';

  useEffect(() => {
    // Calculate total typing time: chars * speed + initialDelay
    const totalTypingTime = fullText.length * TYPING_SPEED + 300; // 300ms initial delay
    const timer = setTimeout(() => {
      setTypingDone(true);
    }, totalTypingTime);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div ref={containerRef} className="splash-screen">
      <div ref={textRef} className="splash-text-wrapper">
        <TextType
          text={fullText}
          as="h1"
          className="splash-heading"
          typingSpeed={TYPING_SPEED}
          initialDelay={300}
          loop={false}
          showCursor
          cursorCharacter="_"
          cursorBlinkDuration={0.4}
          cursorClassName="splash-cursor"
        />
      </div>

      {/* Subtle subtitle that fades in after a delay */}
      <p
        className="splash-subtitle"
        style={{
          opacity: 0,
          animation: typingDone ? 'splashSubFadeIn 0.8s ease forwards' : 'none',
        }}
      >
        TICKET ANALYSIS &amp; REPORTING SYSTEM
      </p>
    </div>
  );
};

export default SplashScreen;
