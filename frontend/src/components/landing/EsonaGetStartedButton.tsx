'use client';

import React from 'react';

interface EsonaGetStartedButtonProps {
  onClick?: () => void;
}

export default function EsonaGetStartedButton({ onClick }: EsonaGetStartedButtonProps) {
  return (
    <div className="esona-btn-container">
      {/* Inline styles for keyframe animations, responsive values, and custom transitions */}
      <style jsx global>{`
        .esona-btn-container {
          width: 280px;
          height: 52px;
          display: inline-flex;
          position: relative;
          animation: button-float 4s ease-in-out infinite;
          z-index: 10;
        }

        @media (max-width: 1024px) {
          .esona-btn-container {
            width: 240px;
            height: 48px;
          }
        }

        @media (max-width: 640px) {
          .esona-btn-container {
            width: 220px;
            height: 46px;
          }
        }

        .esona-btn {
          width: 100%;
          height: 100%;
          position: relative;
          background: rgba(10, 15, 30, 0.8);
          border: 1px solid rgba(56, 189, 248, 0.3);
          border-radius: 8px;
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          color: #FFFFFF;
          font-family: 'Poppins', sans-serif;
          font-size: 16px;
          font-weight: 600;
          letter-spacing: 0.5px;
          cursor: pointer;
          box-shadow: 0 0 15px rgba(56, 189, 248, 0.15), inset 0 0 10px rgba(56, 189, 248, 0.05);
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          z-index: 1;
          overflow: visible;
          display: flex;
          align-items: center;
          justify-content: center;
          user-select: none;
        }

        @media (max-width: 1024px) {
          .esona-btn {
            font-size: 15px;
            letter-spacing: 0.4px;
          }
        }

        @media (max-width: 640px) {
          .esona-btn {
            font-size: 14px;
            letter-spacing: 0.3px;
          }
        }

        /* Gradient Pseudo-element for smooth transition */
        .esona-btn::before {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: 7px; /* Keep slightly smaller than border-radius of button to prevent overflow */
          background: linear-gradient(
            85deg,
            #38BDF8,
            #7C3AED,
            #A855F7,
            #7C3AED,
            #38BDF8
          );
          background-size: 200% auto;
          opacity: 0;
          transition: opacity 0.4s ease-in-out;
          z-index: -1;
        }

        .esona-btn:hover {
          transform: scale(1.04);
          border-color: rgba(168, 85, 247, 0.5);
          box-shadow: 0 0 25px rgba(56, 189, 248, 0.4), 0 0 15px rgba(168, 85, 247, 0.3);
        }

        .esona-btn:hover::before {
          opacity: 1;
          animation: wind-glow 2s linear infinite;
        }

        .esona-btn:active {
          transform: scale(0.96);
          box-shadow: 0 0 30px rgba(56, 189, 248, 0.6), 0 0 20px rgba(168, 85, 247, 0.5);
          transition: all 0.05s ease;
        }

        /* Decorative Elements Positioning */
        .esona-btn .icon-1 {
          position: absolute;
          top: -10px;
          right: -10px;
          width: 25px;
          height: 25px;
          transform-origin: 0 0;
          transform: rotate(10deg);
          transition: all 0.5s ease-in-out;
          filter: drop-shadow(0 0 4px rgba(56, 189, 248, 0.8));
        }

        .esona-btn:hover .icon-1 {
          animation: slay-1 3s cubic-bezier(0.52, 0, 0.58, 1) infinite;
          transform: rotate(10deg);
          filter: drop-shadow(0 0 6px rgba(168, 85, 247, 0.9));
        }

        .esona-btn .icon-2 {
          position: absolute;
          top: -8px;
          left: 25px;
          width: 12px;
          height: 12px;
          transform-origin: 50% 0;
          transform: rotate(10deg);
          transition: all 1s ease-in-out;
          filter: drop-shadow(0 0 3px rgba(56, 189, 248, 0.8));
        }

        .esona-btn:hover .icon-2 {
          animation: slay-2 3s cubic-bezier(0.52, 0, 0.58, 1) 0.5s infinite;
          transform: rotate(0);
          filter: drop-shadow(0 0 5px rgba(168, 85, 247, 0.9));
        }

        .esona-btn .icon-3 {
          position: absolute;
          top: -10px;
          left: -8px;
          width: 18px;
          height: 18px;
          transform-origin: 50% 0;
          transform: rotate(-5deg);
          transition: all 1s ease-in-out;
          filter: drop-shadow(0 0 4px rgba(56, 189, 248, 0.8));
        }

        .esona-btn:hover .icon-3 {
          animation: slay-3 2s cubic-bezier(0.52, 0, 0.58, 1) 0.2s infinite;
          transform: rotate(0);
          filter: drop-shadow(0 0 5px rgba(168, 85, 247, 0.9));
        }

        /* Keyframe Animations */
        @keyframes button-float {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-4px);
          }
        }

        @keyframes wind-glow {
          0% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
          100% {
            background-position: 0% 50%;
          }
        }

        @keyframes slay-1 {
          0%, 100% {
            transform: rotate(10deg);
          }
          50% {
            transform: rotate(-5deg);
          }
        }

        @keyframes slay-2 {
          0%, 100% {
            transform: rotate(0deg);
          }
          50% {
            transform: rotate(15deg);
          }
        }

        @keyframes slay-3 {
          0%, 100% {
            transform: rotate(0deg);
          }
          50% {
            transform: rotate(-8deg);
          }
        }
      `}</style>

      <button className="esona-btn" onClick={onClick}>
        <span>Get Started</span>

        {/* Decorative elements */}
        {/* Icon 1: Pixel Sword */}
        <div className="icon-1">
          <svg viewBox="0 0 16 16" width="100%" height="100%" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Blade (Cyan outer with white core) */}
            <rect x="11" y="3" width="2" height="2" fill="#38BDF8" />
            <rect x="12" y="2" width="2" height="2" fill="#38BDF8" />
            <rect x="13" y="1" width="2" height="2" fill="#38BDF8" />
            <rect x="14" y="0" width="2" height="2" fill="#38BDF8" />
            
            <rect x="12" y="3" width="1" height="1" fill="#FFFFFF" />
            <rect x="13" y="2" width="1" height="1" fill="#FFFFFF" />
            <rect x="14" y="1" width="1" height="1" fill="#FFFFFF" />
            <rect x="15" y="0" width="1" height="1" fill="#FFFFFF" />

            <rect x="10" y="4" width="2" height="2" fill="#0284C7" />
            <rect x="9" y="5" width="2" height="2" fill="#0284C7" />
            <rect x="8" y="6" width="2" height="2" fill="#0284C7" />
            <rect x="7" y="7" width="2" height="2" fill="#0284C7" />

            {/* Crossguard (Purple) */}
            <rect x="5" y="9" width="2" height="2" fill="#A855F7" />
            <rect x="6" y="8" width="2" height="2" fill="#A855F7" />
            <rect x="7" y="7" width="2" height="2" fill="#A855F7" />
            <rect x="8" y="5" width="2" height="2" fill="#A855F7" />
            <rect x="9" y="6" width="2" height="2" fill="#A855F7" />
            <rect x="6" y="9" width="1" height="1" fill="#FFFFFF" />

            {/* Handle (Dark brown) */}
            <rect x="4" y="10" width="2" height="2" fill="#582F0E" />
            <rect x="3" y="11" width="2" height="2" fill="#582F0E" />
            <rect x="2" y="12" width="2" height="2" fill="#582F0E" />

            {/* Pommel (Cyan gem) */}
            <rect x="0" y="14" width="2" height="2" fill="#38BDF8" />
            <rect x="1" y="13" width="2" height="2" fill="#38BDF8" />
            <rect x="1" y="14" width="1" height="1" fill="#FFFFFF" />
          </svg>
        </div>

        {/* Icon 2: Pixel Gem */}
        <div className="icon-2">
          <svg viewBox="0 0 8 8" width="100%" height="100%" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="3" y="0" width="2" height="1" fill="#38BDF8" />
            <rect x="2" y="1" width="4" height="1" fill="#38BDF8" />
            <rect x="1" y="2" width="6" height="2" fill="#38BDF8" />
            <rect x="2" y="4" width="4" height="2" fill="#38BDF8" />
            <rect x="3" y="6" width="2" height="2" fill="#38BDF8" />
            {/* Highlights */}
            <rect x="3" y="2" width="2" height="2" fill="#A855F7" />
            <rect x="3" y="2" width="1" height="1" fill="#FFFFFF" />
          </svg>
        </div>

        {/* Icon 3: Pixel Shield */}
        <div className="icon-3">
          <svg viewBox="0 0 10 10" width="100%" height="100%" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Border */}
            <rect x="1" y="0" width="8" height="1" fill="#1E1B4B" />
            <rect x="0" y="1" width="1" height="6" fill="#1E1B4B" />
            <rect x="9" y="1" width="1" height="6" fill="#1E1B4B" />
            <rect x="1" y="7" width="1" height="1" fill="#1E1B4B" />
            <rect x="8" y="7" width="1" height="1" fill="#1E1B4B" />
            <rect x="2" y="8" width="2" height="1" fill="#1E1B4B" />
            <rect x="6" y="8" width="2" height="1" fill="#1E1B4B" />
            <rect x="4" y="9" width="2" height="1" fill="#1E1B4B" />

            {/* Inner Cyan Fill */}
            <rect x="1" y="1" width="8" height="1" fill="#38BDF8" />
            <rect x="1" y="2" width="1" height="5" fill="#38BDF8" />
            <rect x="8" y="2" width="1" height="5" fill="#38BDF8" />
            <rect x="2" y="7" width="6" height="1" fill="#38BDF8" />
            <rect x="3" y="8" width="4" height="1" fill="#38BDF8" />

            {/* Center Purple Emblem */}
            <rect x="3" y="3" width="4" height="3" fill="#A855F7" />
            <rect x="4" y="6" width="2" height="1" fill="#A855F7" />
            <rect x="4" y="3" width="1" height="1" fill="#FFFFFF" />
          </svg>
        </div>
      </button>
    </div>
  );
}
