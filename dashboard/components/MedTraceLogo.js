'use client';
import { useState } from 'react';

/**
 * MedTraceLogo
 * High-fidelity vector recreation of the master 3D emblem (media_1794644527080_233ddc1e.jpg)
 * and multi-stage hover/click animation (media_1794644473515_d0a51aa4.mp4).
 *
 * Geometry:
 * - 3D hollow tubular medical cross with blue-to-teal gradient.
 * - 45-degree rising audit graph with central diamond loop and projecting input/output nodes.
 * - Precision silver/grey collar beads with glowing green/cyan cores.
 * - 3D bevelled "MedTrace" wordmark.
 * - Multi-stage hover & click animation: S-ribbon energy sweep, specular sheen, sparkles.
 */
export default function MedTraceLogo({ className = '', size = 'default' }) {
  const [active, setActive] = useState(false);

  const triggerAnimation = () => {
    setActive(true);
    setTimeout(() => setActive(false), 1400);
  };

  const isCompact = size === 'compact';

  return (
    <div
      className={`medtrace-logo-wrap ${isCompact ? 'compact' : ''} ${active ? 'is-animating' : ''} ${className}`}
      onClick={triggerAnimation}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          triggerAnimation();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label="MedTrace Logo"
      title="MedTrace - Click to trigger energy sweep"
    >
      <svg
        className="medtrace-logo-svg"
        viewBox={isCompact ? '0 0 48 48' : '0 0 216 46'}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          {/* Master 3D Cross Gradients */}
          <linearGradient id="mt-cross-body" x1="4" y1="42" x2="42" y2="4" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#0284C7" />
            <stop offset="28%" stopColor="#0EA5E9" />
            <stop offset="65%" stopColor="#06B6D4" />
            <stop offset="85%" stopColor="#2DD4BF" />
            <stop offset="100%" stopColor="#10B981" />
          </linearGradient>

          {/* Top/Left Specular Highlight on Cross Rim */}
          <linearGradient id="mt-cross-rim-light" x1="6" y1="6" x2="36" y2="20" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#E0F2FE" stopOpacity="0.9" />
            <stop offset="60%" stopColor="#38BDF8" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#5EEAD4" stopOpacity="0.7" />
          </linearGradient>

          {/* Bottom/Right Shadow for 3D Depth */}
          <linearGradient id="mt-cross-depth-shadow" x1="16" y1="16" x2="44" y2="44" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#0369A1" stopOpacity="0.3" />
            <stop offset="70%" stopColor="#082F49" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#021C2F" stopOpacity="0.95" />
          </linearGradient>

          {/* Graph Connecting Rod Gradient */}
          <linearGradient id="mt-rod-grad" x1="5" y1="33" x2="41" y2="13" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#0284C7" />
            <stop offset="35%" stopColor="#38BDF8" />
            <stop offset="65%" stopColor="#2DD4BF" />
            <stop offset="100%" stopColor="#34D399" />
          </linearGradient>

          {/* Metallic Silver Collar Gradient for Nodes */}
          <linearGradient id="mt-collar-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#F8FAFC" />
            <stop offset="45%" stopColor="#CBD5E1" />
            <stop offset="75%" stopColor="#64748B" />
            <stop offset="100%" stopColor="#94A3B8" />
          </linearGradient>

          {/* Glowing Green Core for Nodes */}
          <radialGradient id="mt-core-green" cx="35%" cy="35%" r="65%">
            <stop offset="0%" stopColor="#A7F3D0" />
            <stop offset="45%" stopColor="#10B981" />
            <stop offset="100%" stopColor="#047857" />
          </radialGradient>

          {/* Glowing Cyan Core for Nodes */}
          <radialGradient id="mt-core-cyan" cx="35%" cy="35%" r="65%">
            <stop offset="0%" stopColor="#E0F2FE" />
            <stop offset="45%" stopColor="#06B6D4" />
            <stop offset="100%" stopColor="#0369A1" />
          </radialGradient>

          {/* Wordmark 3D Gradients */}
          <linearGradient id="mt-wordmark-trace" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#06B6D4" />
            <stop offset="50%" stopColor="#2DD4BF" />
            <stop offset="100%" stopColor="#38BDF8" />
          </linearGradient>

          {/* S-Ribbon Energetic Sweep Gradient */}
          <linearGradient id="mt-ribbon-grad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#2DD4BF" stopOpacity="0" />
            <stop offset="25%" stopColor="#2DD4BF" stopOpacity="0.85" />
            <stop offset="50%" stopColor="#FFFFFF" stopOpacity="1" />
            <stop offset="75%" stopColor="#38BDF8" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#0EA5E9" stopOpacity="0" />
          </linearGradient>

          {/* Specular Diagonal Light Sheen */}
          <linearGradient id="mt-sheen-grad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0" />
            <stop offset="35%" stopColor="#FFFFFF" stopOpacity="0.12" />
            <stop offset="50%" stopColor="#FFFFFF" stopOpacity="0.95" />
            <stop offset="65%" stopColor="#FFFFFF" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
          </linearGradient>

          {/* Glow Filters */}
          <filter id="mt-node-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="1.2" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>

          <filter id="mt-ribbon-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2.2" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>

          {/* Specular Sheen Mask */}
          <mask id="mt-master-sheen-mask">
            {/* Cross outer mask */}
            <path
              d="M 17 5 C 17 3.5 18.2 2.5 19.8 2.5 L 26.2 2.5 C 27.8 2.5 29 3.5 29 5 L 29 15 L 39 15 C 40.5 15 41.5 16.2 41.5 17.8 L 41.5 24.2 C 41.5 25.8 40.5 27 39 27 L 29 27 L 29 37 C 29 38.5 27.8 39.5 26.2 39.5 L 19.8 39.5 C 18.2 39.5 17 38.5 17 37 L 17 27 L 7 27 C 5.5 27 4.5 25.8 4.5 24.2 L 4.5 17.8 C 4.5 16.2 5.5 15 7 15 L 17 15 Z"
              fill="#FFFFFF"
            />
            {!isCompact ? (
              <text
                x="52"
                y="29"
                fill="#FFFFFF"
                fontFamily="Public Sans, system-ui, sans-serif"
                fontWeight="700"
                fontSize="22"
                letterSpacing="-0.03em"
              >
                MedTrace
              </text>
            ) : null}
          </mask>
        </defs>

        {/* ============================================================ */}
        {/* 1. MASTER 3D BEVELLED HOLLOW CROSS EMBLEM                    */}
        {/* ============================================================ */}
        <g className="master-cross-group">
          {/* Ambient Drop Shadow */}
          <path
            d="M 17 7 C 17 5.2 18.2 4 20 4 L 26 4 C 27.8 4 29 5.2 29 7 L 29 16.5 L 38.5 16.5 C 40.3 16.5 41.5 17.7 41.5 19.5 L 41.5 25.5 C 41.5 27.3 40.3 28.5 38.5 28.5 L 29 28.5 L 29 38 C 29 39.8 27.8 41 26 41 L 20 41 C 18.2 41 17 39.8 17 38 L 17 28.5 L 7.5 28.5 C 5.7 28.5 4.5 27.3 4.5 25.5 L 4.5 19.5 C 4.5 17.7 5.7 16.5 7.5 16.5 L 17 16.5 Z"
            fill="rgba(0, 0, 0, 0.55)"
            transform="translate(1, 2.5)"
          />

          {/* 3D Deep Side Extrusion */}
          <path
            d="M 17 6 C 17 4.2 18.2 3 20 3 L 26 3 C 27.8 3 29 4.2 29 6 L 29 16 L 39 16 C 40.8 16 42 17.2 42 19 L 42 25 C 42 26.8 40.8 28 39 28 L 29 28 L 29 38 C 29 39.8 27.8 41 26 41 L 20 41 C 18.2 41 17 39.8 17 38 L 17 28 L 7 28 C 5.2 28 4 26.8 4 25 L 4 19 C 4 17.2 5.2 16 7 16 L 17 16 Z"
            fill="url(#mt-cross-depth-shadow)"
            transform="translate(0.6, 1.2)"
          />

          {/* Outer Rounded Cross Frame */}
          <path
            d="M 17 5 C 17 3.5 18.2 2.5 19.8 2.5 L 26.2 2.5 C 27.8 2.5 29 3.5 29 5 L 29 15 L 39 15 C 40.5 15 41.5 16.2 41.5 17.8 L 41.5 24.2 C 41.5 25.8 40.5 27 39 27 L 29 27 L 29 37 C 29 38.5 27.8 39.5 26.2 39.5 L 19.8 39.5 C 18.2 39.5 17 38.5 17 37 L 17 27 L 7 27 C 5.5 27 4.5 25.8 4.5 24.2 L 4.5 17.8 C 4.5 16.2 5.5 15 7 15 L 17 15 Z"
            fill="url(#mt-cross-body)"
          />

          {/* Hollow Aperture Inner Cutout */}
          <path
            d="M 19.5 12 C 19.5 11 20.2 10.5 21.2 10.5 L 24.8 10.5 C 25.8 10.5 26.5 11 26.5 12 L 26.5 18 L 32.5 18 C 33.5 18 34 18.7 34 19.7 L 34 22.3 C 34 23.3 33.5 24 32.5 24 L 26.5 24 L 26.5 30 C 26.5 31 25.8 31.5 24.8 31.5 L 21.2 31.5 C 20.2 31.5 19.5 31 19.5 30 L 19.5 24 L 13.5 24 C 12.5 24 12 23.3 12 22.3 L 12 19.7 C 12 18.7 12.5 18 13.5 18 L 19.5 18 Z"
            fill="var(--bg-base, #080A0E)"
            stroke="url(#mt-cross-depth-shadow)"
            strokeWidth="0.8"
          />

          {/* Top/Left Specular Highlight Rim */}
          <path
            d="M 19.8 2.5 L 26.2 2.5 C 27.8 2.5 29 3.5 29 5 L 29 6.5 L 19.8 6.5 Z M 4.5 17.8 L 4.5 24.2 L 6 24.2 L 6 17.8 Z M 17 15 L 7 15 C 5.5 15 4.5 16.2 4.5 17.8 L 6 17.8 L 17 16.5 Z M 29 15 L 39 15 C 40.5 15 41.5 16.2 41.5 17.8 L 40 17.8 L 29 16.5 Z"
            fill="url(#mt-cross-rim-light)"
          />
        </g>

        {/* ============================================================ */}
        {/* 2. 5-NODE RISING GRAPH WITH CENTRAL DIAMOND AUDIT LOOP       */}
        {/* ============================================================ */}
        <g className="master-graph-group">
          {/* Shadow for graph rods */}
          <g transform="translate(0.8, 1.2)" opacity="0.45">
            <line x1="5.5" y1="32.5" x2="14.5" y2="23.5" stroke="#000" strokeWidth="2.2" strokeLinecap="round" />
            <polygon points="14.5,23.5 23,15 31.5,23.5 23,32" stroke="#000" strokeWidth="2.2" fill="none" />
            <line x1="31.5" y1="23.5" x2="40.5" y2="14.5" stroke="#000" strokeWidth="2.2" strokeLinecap="round" />
          </g>

          {/* Connecting Input Rod: (5.5, 32.5) -> (14.5, 23.5) */}
          <line
            x1="5.5"
            y1="32.5"
            x2="14.5"
            y2="23.5"
            stroke="url(#mt-rod-grad)"
            strokeWidth="2.4"
            strokeLinecap="round"
          />

          {/* Central Diamond Audit Loop */}
          <polygon
            points="14.5,23.5 23,15 31.5,23.5 23,32"
            fill="rgba(45, 212, 191, 0.08)"
            stroke="url(#mt-rod-grad)"
            strokeWidth="2.4"
            strokeLinejoin="round"
          />

          {/* Connecting Output Rod: (31.5, 23.5) -> (40.5, 14.5) */}
          <line
            x1="31.5"
            y1="23.5"
            x2="40.5"
            y2="14.5"
            stroke="url(#mt-rod-grad)"
            strokeWidth="2.4"
            strokeLinecap="round"
          />

          {/* Node 1: Bottom-Left Projecting Exterior Node */}
          <g transform="translate(5.5, 32.5)" filter="url(#mt-node-glow)">
            <circle cx="0" cy="0" r="3.2" fill="url(#mt-collar-grad)" stroke="#1E293B" strokeWidth="0.5" />
            <circle cx="0" cy="0" r="1.8" fill="url(#mt-core-green)" />
          </g>

          {/* Node 2: Left Diamond Junction Node */}
          <g transform="translate(14.5, 23.5)">
            <circle cx="0" cy="0" r="2.8" fill="url(#mt-collar-grad)" stroke="#1E293B" strokeWidth="0.5" />
            <circle cx="0" cy="0" r="1.5" fill="url(#mt-core-cyan)" />
          </g>

          {/* Node 3: Top Diamond Peak Node */}
          <g transform="translate(23, 15)">
            <circle cx="0" cy="0" r="2.8" fill="url(#mt-collar-grad)" stroke="#1E293B" strokeWidth="0.5" />
            <circle cx="0" cy="0" r="1.5" fill="url(#mt-core-cyan)" />
          </g>

          {/* Node 4: Bottom Diamond Node */}
          <g transform="translate(23, 32)">
            <circle cx="0" cy="0" r="2.8" fill="url(#mt-collar-grad)" stroke="#1E293B" strokeWidth="0.5" />
            <circle cx="0" cy="0" r="1.5" fill="url(#mt-core-cyan)" />
          </g>

          {/* Node 5: Right Diamond Junction Node */}
          <g transform="translate(31.5, 23.5)">
            <circle cx="0" cy="0" r="2.8" fill="url(#mt-collar-grad)" stroke="#1E293B" strokeWidth="0.5" />
            <circle cx="0" cy="0" r="1.5" fill="url(#mt-core-cyan)" />
          </g>

          {/* Node 6: Top-Right Projecting Exterior Node */}
          <g transform="translate(40.5, 14.5)" filter="url(#mt-node-glow)">
            <circle cx="0" cy="0" r="3.4" fill="url(#mt-collar-grad)" stroke="#1E293B" strokeWidth="0.5" />
            <circle cx="0" cy="0" r="2.0" fill="url(#mt-core-green)" />
          </g>
        </g>

        {/* ============================================================ */}
        {/* 3. WORDMARK: "MedTrace"                                     */}
        {/* ============================================================ */}
        {!isCompact ? (
          <g className="master-wordmark-group">
            {/* 3D Drop Depth Shadow for text */}
            <text
              x="52"
              y="30.2"
              fontFamily="Public Sans, system-ui, -apple-system, sans-serif"
              fontWeight="700"
              fontSize="22"
              letterSpacing="-0.03em"
              fill="rgba(0, 0, 0, 0.45)"
            >
              MedTrace
            </text>

            {/* Front Crisp Letters */}
            <text
              x="52"
              y="29"
              fontFamily="Public Sans, system-ui, -apple-system, sans-serif"
              fontWeight="700"
              fontSize="22"
              letterSpacing="-0.03em"
            >
              <tspan className="wordmark-med" fill="var(--text-primary, #F1F5F9)">
                Med
              </tspan>
              <tspan className="wordmark-trace" fill="url(#mt-wordmark-trace)">
                Trace
              </tspan>
            </text>
          </g>
        ) : null}

        {/* ============================================================ */}
        {/* 4. ANIMATION: DIAGONAL SPECULAR LIGHT SHEEN                  */}
        {/* ============================================================ */}
        <g mask="url(#mt-master-sheen-mask)" className="logo-sheen-layer">
          <rect
            className="logo-sheen-rect"
            x="-140"
            y="-20"
            width="90"
            height="90"
            fill="url(#mt-sheen-grad)"
            transform="rotate(25 40 20)"
          />
        </g>

        {/* ============================================================ */}
        {/* 5. ANIMATION: LUMINOUS CURVED S-RIBBON ENERGY SWEEP          */}
        {/* ============================================================ */}
        <g className="logo-ribbon-layer" filter="url(#mt-ribbon-glow)">
          <path
            className="logo-s-ribbon"
            d={
              isCompact
                ? 'M -10 36 C 8 40, 16 6, 26 22 S 38 12, 54 24'
                : 'M -15 38 C 12 44, 24 6, 46 22 S 90 40, 130 18 S 175 12, 215 26'
            }
            fill="none"
            stroke="url(#mt-ribbon-grad)"
            strokeWidth="3.4"
            strokeLinecap="round"
          />
        </g>

        {/* ============================================================ */}
        {/* 6. ANIMATION: DRIFTING CYAN/WHITE SPARKLE PARTICLES          */}
        {/* ============================================================ */}
        <g className="logo-sparkles-layer">
          <circle className="logo-sparkle sp-1" cx="5.5" cy="32.5" r="1.3" fill="#A7F3D0" />
          <circle className="logo-sparkle sp-2" cx="23" cy="15" r="1.4" fill="#38BDF8" />
          <circle className="logo-sparkle sp-3" cx="40.5" cy="14.5" r="1.5" fill="#FFFFFF" />
          <circle className="logo-sparkle sp-4" cx="31.5" cy="23.5" r="1.2" fill="#5EEAD4" />
        </g>
      </svg>
    </div>
  );
}
