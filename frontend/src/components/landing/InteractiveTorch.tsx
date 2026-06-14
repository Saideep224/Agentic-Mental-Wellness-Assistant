'use client';

import { useState } from 'react';
import styles from './InteractiveTorch.module.css';

interface Props {
  onLight?: () => void;
}

export default function InteractiveTorch({ onLight }: Props) {
  const [isLit, setIsLit] = useState(false);

  const handleLight = () => {
    if (!isLit) {
      setIsLit(true);
      if (onLight) onLight();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleLight();
    }
  };

  return (
    <div
      className={`${styles.container} ${isLit ? styles.lit : ''}`}
      onClick={handleLight}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label={isLit ? "Torch is lit" : "Light the torch"}
    >
      <div className={styles.torch}>
        <div className={styles.head}>
          <div className={styles.face}>
            <div className={styles.sparkles} />
            <div className={styles.top}>
              <div />
              <div />
              <div />
              <div />
            </div>
            <div className={styles.left}>
              <div />
              <div />
              <div />
              <div />
            </div>
            <div className={styles.right}>
              <div />
              <div />
              <div />
              <div />
            </div>
          </div>
        </div>
        <div className={styles.stick}>
          <div className={`${styles.side} ${styles.sideLeft}`}>
            {Array.from({ length: 16 }).map((_, i) => (
              <div key={`left-${i}`} />
            ))}
          </div>
          <div className={`${styles.side} ${styles.sideRight}`}>
            {Array.from({ length: 16 }).map((_, i) => (
              <div key={`right-${i}`} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
