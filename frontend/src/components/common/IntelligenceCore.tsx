export function IntelligenceCore({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`intelligence-core ${compact ? 'compact' : ''}`} aria-hidden="true">
      <svg viewBox="0 0 320 320" fill="none">
        <defs>
          <radialGradient id="coreGlow">
            <stop stopColor="#21d4ed" stopOpacity=".12" />
            <stop offset="1" stopColor="#21d4ed" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="160" cy="160" r="158" fill="url(#coreGlow)" />
        <g className="outer-orbit">
          <circle cx="160" cy="160" r="145" stroke="#1a647e" strokeWidth="1" />
          <circle
            cx="160"
            cy="160"
            r="145"
            stroke="#43dff4"
            strokeWidth="3"
            strokeDasharray="80 148 12 125 42 100 60 345"
          />
          <circle
            cx="160"
            cy="160"
            r="132"
            stroke="#167392"
            strokeDasharray="2 12"
            strokeWidth="3"
          />
        </g>
        <circle cx="160" cy="160" r="116" stroke="#17506a" strokeWidth="1" />
        <circle
          cx="160"
          cy="160"
          r="109"
          stroke="#44cfe6"
          strokeWidth="5"
          strokeDasharray="2 5"
          opacity=".7"
        />
        <circle
          cx="160"
          cy="160"
          r="96"
          stroke="#32d9ef"
          strokeWidth="2"
          strokeDasharray="270 50 125 160"
        />
        <circle cx="160" cy="160" r="88" stroke="#1b667e" strokeWidth="1" />
        <path d="M148 87h24M87 148v24m61 61h24m61-85v24" stroke="#91edfa" strokeWidth="3" />
        <path d="m141 166 19-38 19 38m-31-12h24" stroke="#8aeeff" strokeWidth="2.5" />
        <text
          x="160"
          y="192"
          textAnchor="middle"
          fill="#aceffc"
          fontFamily="monospace"
          fontSize="11"
          letterSpacing="5"
        >
          AETHER
        </text>
        <text
          x="160"
          y="209"
          textAnchor="middle"
          fill="#5293a7"
          fontFamily="monospace"
          fontSize="6"
          letterSpacing="2"
        >
          RESEARCH INTELLIGENCE
        </text>
      </svg>
    </div>
  );
}
