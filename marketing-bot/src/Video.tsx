import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/NotoSansHebrew";

const { fontFamily } = loadFont();

// ── Palette ───────────────────────────────────────────────────────────────────
const INDIGO   = "#1E0050";
const PURPLE   = "#7C3AED";
const PURPLE_L = "#A78BFA";
const CYAN     = "#06B6D4";
const GOLD     = "#FBBF24";
const WHITE    = "#FFFFFF";
const BLACK    = "#000000";

// ── Spring helpers ────────────────────────────────────────────────────────────
const useSpr = (
  start: number,
  cfg = { damping: 12, stiffness: 120 }
) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ fps, frame: frame - start, config: cfg });
};

const useFade = (start: number, end: number) => {
  const frame = useCurrentFrame();
  return interpolate(frame, [start, end], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
};

// ══════════════════════════════════════════════════════════════════════════════
//  Animated Background — deep indigo → black with roaming orbs
// ══════════════════════════════════════════════════════════════════════════════
const Background: React.FC = () => {
  const frame = useCurrentFrame();

  const shift1 = 50 + 20 * Math.sin((frame / 90) * Math.PI);
  const shift2 = 50 + 15 * Math.cos((frame / 110) * Math.PI);
  const orb1x  = 30 + 12 * Math.sin((frame / 80)  * Math.PI);
  const orb1y  = 20 + 10 * Math.cos((frame / 100) * Math.PI);
  const orb2x  = 70 + 10 * Math.cos((frame / 95)  * Math.PI);
  const orb2y  = 70 + 12 * Math.sin((frame / 85)  * Math.PI);

  return (
    <AbsoluteFill>
      {/* Base gradient */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at ${shift1}% ${shift2}%, ${INDIGO} 0%, #0D0020 45%, ${BLACK} 100%)`,
        }}
      />
      {/* Roaming orb 1 — purple */}
      <div
        style={{
          position: "absolute",
          width: 700,
          height: 700,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${PURPLE}30 0%, transparent 70%)`,
          top: `${orb1y}%`,
          left: `${orb1x}%`,
          transform: "translate(-50%, -50%)",
          filter: "blur(2px)",
        }}
      />
      {/* Roaming orb 2 — cyan */}
      <div
        style={{
          position: "absolute",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${CYAN}20 0%, transparent 70%)`,
          top: `${orb2y}%`,
          left: `${orb2x}%`,
          transform: "translate(-50%, -50%)",
        }}
      />
      {/* Dot grid */}
      <AbsoluteFill
        style={{
          backgroundImage: `radial-gradient(circle, rgba(124,58,237,0.18) 1px, transparent 1px)`,
          backgroundSize: "52px 52px",
        }}
      />
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  Glowing Logo "B"
// ══════════════════════════════════════════════════════════════════════════════
const GlowLogo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Overshoot spring for entry
  const entry = spring({ fps, frame, config: { damping: 6, stiffness: 180 } });
  const scale = interpolate(entry, [0, 1], [0, 1]);
  const op    = useFade(0, 8);

  // Continuous pulse glow
  const pulse  = 1 + 0.06 * Math.sin((frame / fps) * Math.PI * 1.4);
  const glow1  = 30 + 15 * Math.sin((frame / fps) * Math.PI * 1.4);
  const glow2  = 60 + 20 * Math.sin((frame / fps) * Math.PI * 1.4);
  const glow3  = 90 + 25 * Math.sin((frame / fps) * Math.PI * 1.4);

  return (
    <div
      style={{
        opacity: op,
        transform: `scale(${scale * pulse})`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 0,
      }}
    >
      {/* Outer glow ring */}
      <div
        style={{
          width: 200,
          height: 200,
          borderRadius: "50%",
          background: `conic-gradient(from 0deg, ${PURPLE}, ${CYAN}, ${GOLD}, ${PURPLE})`,
          padding: 4,
          boxShadow: [
            `0 0 ${glow1}px ${PURPLE}`,
            `0 0 ${glow2}px ${PURPLE}80`,
            `0 0 ${glow3}px ${CYAN}40`,
          ].join(", "),
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Inner circle */}
        <div
          style={{
            width: "calc(100% - 8px)",
            height: "calc(100% - 8px)",
            borderRadius: "50%",
            background: `radial-gradient(circle at 35% 35%, #2D0070, #0D0020)`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span
            style={{
              fontSize: 110,
              fontWeight: 900,
              color: WHITE,
              fontFamily,
              lineHeight: 1,
              textShadow: `0 0 20px ${PURPLE}, 0 0 40px ${CYAN}80`,
            }}
          >
            B
          </span>
        </div>
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  Bouncing Headline — spring with massive overshoot
// ══════════════════════════════════════════════════════════════════════════════
const Headline: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entry = spring({ fps, frame, config: { damping: 5, stiffness: 200 } });
  const scale = interpolate(entry, [0, 1], [0.5, 1]);
  const op    = useFade(0, 6);
  const glow  = 12 + 8 * Math.sin((frame / fps) * Math.PI * 1.2);

  return (
    <div style={{ opacity: op, transform: `scale(${scale})`, textAlign: "center", direction: "rtl" }}>
      {/* Brand name */}
      <div
        style={{
          fontSize: 108,
          fontWeight: 900,
          fontFamily,
          background: `linear-gradient(135deg, ${WHITE} 0%, ${PURPLE_L} 50%, ${CYAN} 100%)`,
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          letterSpacing: -2,
          lineHeight: 1,
          filter: `drop-shadow(0 0 ${glow}px ${PURPLE}80)`,
        }}
      >
        Boostly
      </div>

      {/* Separator */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 16, margin: "16px 0" }}>
        <div style={{ flex: 1, height: 2, background: `linear-gradient(90deg, transparent, ${GOLD})` }} />
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: GOLD }} />
        <div style={{ flex: 1, height: 2, background: `linear-gradient(90deg, ${GOLD}, transparent)` }} />
      </div>

      {/* Hebrew tagline */}
      <div
        style={{
          fontSize: 64,
          fontWeight: 700,
          fontFamily,
          color: WHITE,
          lineHeight: 1.3,
          textShadow: `0 2px 24px rgba(0,0,0,0.8)`,
        }}
      >
        הופכים תנועה ללקוחות
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  Sub Headline
// ══════════════════════════════════════════════════════════════════════════════
const SubHeadline: React.FC = () => {
  const spr = useSpr(0, { damping: 14, stiffness: 100 });
  const y   = interpolate(spr, [0, 1], [50, 0]);
  const op  = useFade(0, 12);

  return (
    <div
      style={{
        opacity: op,
        transform: `translateY(${y}px)`,
        textAlign: "center",
        direction: "rtl",
      }}
    >
      <div
        style={{
          fontSize: 44,
          fontWeight: 400,
          fontFamily,
          color: `rgba(255,255,255,0.70)`,
          letterSpacing: 1,
        }}
      >
        אוטומציה שיווקית ברמה אחרת
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  SVG Growth Line — animated strokeDashoffset
// ══════════════════════════════════════════════════════════════════════════════
const GrowthLine: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const PATH_LENGTH = 900;

  // Animate from full dash (invisible) to 0 (fully visible)
  const prog    = spring({ fps, frame, config: { damping: 18, stiffness: 60 } });
  const dashOff = interpolate(prog, [0, 1], [PATH_LENGTH, 0]);
  const op      = useFade(0, 10);

  // Glow pulse
  const glow = 4 + 3 * Math.sin((frame / fps) * Math.PI * 2);

  return (
    <div style={{ opacity: op, position: "absolute", width: "100%", height: "100%" }}>
      <svg
        width="1080"
        height="1920"
        viewBox="0 0 1080 1920"
        style={{ position: "absolute", top: 0, left: 0 }}
      >
        <defs>
          <linearGradient id="lineGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor={PURPLE} stopOpacity="0.2" />
            <stop offset="40%"  stopColor={PURPLE} stopOpacity="0.9" />
            <stop offset="70%"  stopColor={CYAN}   stopOpacity="1"   />
            <stop offset="100%" stopColor={GOLD}   stopOpacity="1"   />
          </linearGradient>
          <filter id="lineGlow">
            <feGaussianBlur stdDeviation={glow} result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Main growth path — diagonal wave upward */}
        <path
          d="M 80 1750 C 150 1600, 200 1500, 280 1380 S 380 1200, 440 1080 S 520 900, 580 760 S 660 580, 720 460 S 820 300, 920 180 S 980 120, 1020 80"
          fill="none"
          stroke="url(#lineGrad)"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={PATH_LENGTH}
          strokeDashoffset={dashOff}
          filter="url(#lineGlow)"
        />

        {/* Glowing dot at the tip */}
        {prog > 0.1 && (
          <>
            <circle
              cx={interpolate(prog, [0, 1], [80, 1020])}
              cy={interpolate(prog, [0, 1], [1750, 80])}
              r={10 + 4 * Math.sin((frame / fps) * Math.PI * 3)}
              fill={CYAN}
              opacity={0.9}
            />
            <circle
              cx={interpolate(prog, [0, 1], [80, 1020])}
              cy={interpolate(prog, [0, 1], [1750, 80])}
              r={20 + 8 * Math.sin((frame / fps) * Math.PI * 3)}
              fill={CYAN}
              opacity={0.3}
            />
          </>
        )}

        {/* Arrow head at top */}
        {prog > 0.85 && (
          <polygon
            points="1020,60 1005,100 1035,100"
            fill={GOLD}
            opacity={interpolate(prog, [0.85, 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}
          />
        )}
      </svg>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  Glassmorphism Stats Cards
// ══════════════════════════════════════════════════════════════════════════════
const STATS = [
  { value: "50K+",  label: "לקוחות",     color: PURPLE, icon: "👥" },
  { value: "2M+",   label: "הזמנות",     color: CYAN,   icon: "📦" },
  { value: "99%",   label: "שביעות רצון", color: GOLD,   icon: "⭐" },
];

const GlassCard: React.FC<{ value: string; label: string; color: string; icon: string; delay: number }> = ({
  value, label, color, icon, delay,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const spr  = spring({ fps, frame: frame - delay, config: { damping: 10, stiffness: 130 } });
  const y    = interpolate(spr, [0, 1], [100, 0]);
  const op   = interpolate(frame - delay, [0, 12], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const valSpr   = spring({ fps, frame: frame - delay - 5, config: { damping: 5, stiffness: 200 } });
  const valScale = interpolate(valSpr, [0, 1], [0.6, 1]);

  return (
    <div
      style={{
        opacity: op,
        transform: `translateY(${y}px)`,
        background: "rgba(255,255,255,0.06)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        border: `1.5px solid rgba(255,255,255,0.12)`,
        borderRadius: 32,
        padding: "36px 40px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
        minWidth: 260,
        boxShadow: `0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)`,
      }}
    >
      <div style={{ fontSize: 52 }}>{icon}</div>
      <div
        style={{
          fontSize: 72,
          fontWeight: 900,
          fontFamily,
          color,
          transform: `scale(${valScale})`,
          textShadow: `0 0 24px ${color}80`,
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      <div style={{ fontSize: 32, color: "rgba(255,255,255,0.7)", fontFamily, direction: "rtl" }}>
        {label}
      </div>
    </div>
  );
};

const StatsRow: React.FC = () => (
  <div style={{ display: "flex", gap: 28, justifyContent: "center", flexWrap: "wrap" }}>
    {STATS.map((s, i) => (
      <GlassCard key={s.label} {...s} delay={i * 12} />
    ))}
  </div>
);

// ══════════════════════════════════════════════════════════════════════════════
//  CTA — Pulsing button
// ══════════════════════════════════════════════════════════════════════════════
const CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const spr    = spring({ fps, frame, config: { damping: 7, stiffness: 160 } });
  const scale  = interpolate(spr, [0, 1], [0.3, 1]);
  const op     = useFade(0, 10);
  const pulse  = 1 + 0.04 * Math.sin((frame / fps) * Math.PI * 2.2);
  const glow   = 20 + 12 * Math.sin((frame / fps) * Math.PI * 2.2);

  return (
    <div style={{ opacity: op, transform: `scale(${scale})`, display: "flex", flexDirection: "column", alignItems: "center", gap: 28 }}>
      {/* Main CTA button */}
      <div
        style={{
          transform: `scale(${pulse})`,
          background: `linear-gradient(135deg, ${PURPLE}, #6D28D9)`,
          borderRadius: 999,
          padding: "32px 96px",
          fontSize: 52,
          fontWeight: 900,
          fontFamily,
          color: WHITE,
          direction: "rtl",
          boxShadow: [
            `0 0 ${glow}px ${PURPLE}`,
            `0 0 ${glow * 2}px ${PURPLE}40`,
            `0 16px 48px rgba(0,0,0,0.5)`,
          ].join(", "),
          letterSpacing: 1,
        }}
      >
        ⚡ boostlyshop.com
      </div>

      {/* Sub-note */}
      <div style={{ fontSize: 34, color: "rgba(255,255,255,0.55)", fontFamily, direction: "rtl" }}>
        הרשמה חינמית · 5% בונוס על הטעינה הראשונה
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  Floating Particles
// ══════════════════════════════════════════════════════════════════════════════
const PARTICLES = Array.from({ length: 18 }, (_, i) => ({
  x: (i * 67 + 30) % 90 + 5,
  y: (i * 53 + 10) % 80 + 10,
  size: 2 + (i % 3),
  speed: 0.3 + (i % 4) * 0.15,
  phase: i * 0.7,
  color: i % 3 === 0 ? PURPLE : i % 3 === 1 ? CYAN : GOLD,
}));

const Particles: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const op = useFade(0, 20);

  return (
    <AbsoluteFill style={{ opacity: op * 0.6 }}>
      {PARTICLES.map((p, i) => {
        const drift = Math.sin((frame / fps) * p.speed * Math.PI + p.phase) * 15;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${p.x}%`,
              top: `calc(${p.y}% + ${drift}px)`,
              width: p.size * 2,
              height: p.size * 2,
              borderRadius: "50%",
              background: p.color,
              boxShadow: `0 0 ${p.size * 4}px ${p.color}`,
              opacity: 0.5 + 0.5 * Math.sin((frame / fps) * p.speed * Math.PI * 2 + p.phase),
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  Main Composition — 300 frames = 10 seconds
// ══════════════════════════════════════════════════════════════════════════════
export const Video: React.FC<{ text?: string }> = () => {
  return (
    <AbsoluteFill style={{ fontFamily, direction: "rtl", overflow: "hidden" }}>

      {/* Layer 0: Background */}
      <Background />

      {/* Layer 1: Particles */}
      <Particles />

      {/* Layer 2: Growth SVG line — starts at frame 60 */}
      <Sequence from={60} durationInFrames={240}>
        <GrowthLine />
      </Sequence>

      {/* Layer 3: Content */}
      <AbsoluteFill style={{
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 52,
      }}>

        {/* Logo — frame 0 */}
        <Sequence from={0} durationInFrames={300}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", top: -500 }}>
            <GlowLogo />
          </AbsoluteFill>
        </Sequence>

        {/* Headline — frame 20 */}
        <Sequence from={20} durationInFrames={280}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", top: -150 }}>
            <Headline />
          </AbsoluteFill>
        </Sequence>

        {/* Sub — frame 50 */}
        <Sequence from={50} durationInFrames={250}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", top: 60 }}>
            <SubHeadline />
          </AbsoluteFill>
        </Sequence>

        {/* Stats cards — frame 90 */}
        <Sequence from={90} durationInFrames={210}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", top: 220 }}>
            <StatsRow />
          </AbsoluteFill>
        </Sequence>

        {/* CTA — frame 160 */}
        <Sequence from={160} durationInFrames={140}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", top: 500 }}>
            <CTA />
          </AbsoluteFill>
        </Sequence>

      </AbsoluteFill>

      {/* Progress bar */}
      <ProgressBar />

    </AbsoluteFill>
  );
};

const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const pct   = Math.min(frame / 300, 1) * 100;
  return (
    <div style={{
      position: "absolute", bottom: 0, left: 0,
      width: `${pct}%`, height: 5,
      background: `linear-gradient(90deg, ${PURPLE}, ${CYAN}, ${GOLD})`,
      zIndex: 999,
    }} />
  );
};
