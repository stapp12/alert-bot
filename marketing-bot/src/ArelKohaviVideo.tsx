import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Heebo";

const { fontFamily } = loadFont();

// ── צבעים ────────────────────────────────────────────────────────────────────
const BG       = "#050510";
const CYAN     = "#00D9FF";
const CYAN_D   = "#0099BB";
const PURPLE   = "#8B5CF6";
const GREEN    = "#10B981";
const GOLD     = "#F59E0B";
const WHITE    = "#FFFFFF";
const GRAY     = "rgba(255,255,255,0.6)";
const CARD_BG  = "rgba(255,255,255,0.04)";

// ── עזרים ─────────────────────────────────────────────────────────────────────
const ease = (frame: number, start: number, end: number) =>
  interpolate(frame, [start, end], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
  });

const fadeUp = (frame: number, start: number) => ({
  opacity: interpolate(frame, [start, start + 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
  transform: `translateY(${interpolate(frame, [start, start + 18], [45, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}px)`,
});

const fadeIn = (frame: number, start: number) => ({
  opacity: interpolate(frame, [start, start + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
});

// ── רקע עם grid ───────────────────────────────────────────────────────────────
const GridBg: React.FC<{ accent?: string }> = ({ accent = CYAN }) => (
  <AbsoluteFill style={{ overflow: "hidden" }}>
    {/* Radial glow */}
    <div style={{
      position: "absolute", width: 900, height: 900, borderRadius: "50%",
      background: `radial-gradient(circle, ${accent}18 0%, transparent 65%)`,
      top: "40%", left: "50%", transform: "translate(-50%, -50%)",
    }} />
    {/* Grid lines */}
    <svg width="100%" height="100%" style={{ position: "absolute", opacity: 0.07 }}>
      {Array.from({ length: 20 }).map((_, i) => (
        <line key={`h${i}`} x1="0" y1={i * 96} x2="1080" y2={i * 96}
          stroke={accent} strokeWidth="1" />
      ))}
      {Array.from({ length: 12 }).map((_, i) => (
        <line key={`v${i}`} x1={i * 96} y1="0" x2={i * 96} y2="1920"
          stroke={accent} strokeWidth="1" />
      ))}
    </svg>
    {/* Bottom fade */}
    <div style={{
      position: "absolute", bottom: 0, width: "100%", height: 300,
      background: `linear-gradient(transparent, ${BG})`,
    }} />
  </AbsoluteFill>
);

// ── Scene 1: פתיחה (0-100) ────────────────────────────────────────────────────
const SceneOpening: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ fps, frame, config: { damping: 13, stiffness: 80 } });
  const logoS = interpolate(logoScale, [0, 1], [0.3, 1]);
  const logoOp = interpolate(frame, [0, 18], [0, 1], { extrapolateRight: "clamp" });

  const lineW = interpolate(frame, [25, 55], [0, 520], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 0 }}>
      <GridBg accent={CYAN} />

      {/* שם */}
      <div style={{
        opacity: logoOp,
        transform: `scale(${logoS})`,
        fontFamily,
        textAlign: "center",
        direction: "rtl",
      }}>
        <div style={{
          fontSize: 96, fontWeight: 900, color: WHITE,
          letterSpacing: -2,
          textShadow: `0 0 60px ${CYAN}80`,
          lineHeight: 1.1,
        }}>
          arel kohavi
        </div>
        <div style={{
          fontSize: 38, fontWeight: 400, color: CYAN,
          letterSpacing: 6, textTransform: "uppercase", marginTop: 8,
        }}>
          digital services
        </div>
      </div>

      {/* קו */}
      <div style={{
        width: lineW, height: 2, marginTop: 40,
        background: `linear-gradient(90deg, transparent, ${CYAN}, transparent)`,
        boxShadow: `0 0 16px ${CYAN}`,
      }} />

      {/* תגית */}
      <div style={{
        ...fadeUp(frame, 50),
        marginTop: 40, fontFamily, textAlign: "center", direction: "rtl",
      }}>
        <div style={{ fontSize: 44, fontWeight: 700, color: WHITE }}>
          שירותים דיגיטליים מתקדמים
        </div>
        <div style={{ fontSize: 32, color: GRAY, marginTop: 12 }}>
          מהיר · אנונימי · מובטח
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 2: שחרור חשבונות (100-230) ─────────────────────────────────────────
const SceneUnban: React.FC = () => {
  const frame = useCurrentFrame();

  const services = [
    { name: "WhatsApp", icon: "💬", color: "#25D366" },
    { name: "Instagram", icon: "📸", color: "#E1306C" },
    { name: "TikTok",    icon: "🎵", color: "#69C9D0" },
  ];

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", padding: "0 80px" }}>
      <GridBg accent={GREEN} />

      {/* כותרת */}
      <div style={{ ...fadeUp(frame, 0), fontFamily, textAlign: "center", direction: "rtl", marginBottom: 60 }}>
        <div style={{
          fontSize: 36, color: GREEN, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase",
          marginBottom: 16,
        }}>
          חשבון חסום?
        </div>
        <div style={{ fontSize: 72, fontWeight: 900, color: WHITE, lineHeight: 1.1 }}>
          אנחנו משחררים
        </div>
        <div style={{ fontSize: 72, fontWeight: 900, color: WHITE, lineHeight: 1.1 }}>
          את זה
        </div>
      </div>

      {/* כרטיסי שירות */}
      <div style={{ display: "flex", flexDirection: "column", gap: 28, width: "100%" }}>
        {services.map((svc, i) => {
          const prog = ease(frame, i * 18 + 20, i * 18 + 45);
          return (
            <div key={svc.name} style={{
              opacity: prog,
              transform: `translateX(${interpolate(prog, [0, 1], [80, 0])}px)`,
              display: "flex",
              alignItems: "center",
              background: `${svc.color}15`,
              border: `1.5px solid ${svc.color}50`,
              borderRadius: 24,
              padding: "28px 40px",
              gap: 28,
              direction: "rtl",
              fontFamily,
            }}>
              <div style={{ fontSize: 60 }}>{svc.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 44, fontWeight: 800, color: WHITE }}>{svc.name}</div>
                <div style={{ fontSize: 28, color: GRAY, marginTop: 4 }}>שחרור חשבון חסום</div>
              </div>
              <div style={{
                background: svc.color, color: BG, fontWeight: 800,
                fontSize: 24, padding: "10px 28px", borderRadius: 999,
              }}>
                unban ✓
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 3: סטרימינג (230-360) ───────────────────────────────────────────────
const SceneStreaming: React.FC = () => {
  const frame = useCurrentFrame();

  const services = [
    { name: "Spotify",  icon: "🎧", price: "₪19/חודש",  color: "#1DB954" },
    { name: "YouTube",  icon: "▶️", price: "₪25/חודש",  color: "#FF0000" },
    { name: "Netflix",  icon: "🎬", price: "₪39/חודש",  color: "#E50914" },
  ];

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", padding: "0 80px" }}>
      <GridBg accent={PURPLE} />

      <div style={{ ...fadeUp(frame, 0), fontFamily, textAlign: "center", direction: "rtl", marginBottom: 56 }}>
        <div style={{ fontSize: 36, color: PURPLE, fontWeight: 700, letterSpacing: 2, marginBottom: 16 }}>
          PREMIUM
        </div>
        <div style={{ fontSize: 72, fontWeight: 900, color: WHITE, lineHeight: 1.1 }}>
          מנויי סטרימינג
        </div>
        <div style={{ fontSize: 72, fontWeight: 900, color: WHITE, lineHeight: 1.1 }}>
          במחיר הכי זול
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 26, width: "100%" }}>
        {services.map((svc, i) => {
          const prog = ease(frame, i * 16 + 22, i * 16 + 46);
          return (
            <div key={svc.name} style={{
              opacity: prog,
              transform: `scale(${interpolate(prog, [0, 1], [0.85, 1])})`,
              display: "flex",
              alignItems: "center",
              background: CARD_BG,
              border: `1.5px solid ${svc.color}40`,
              borderRadius: 24,
              padding: "26px 40px",
              gap: 28,
              direction: "rtl",
              fontFamily,
            }}>
              <div style={{ fontSize: 56 }}>{svc.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 44, fontWeight: 800, color: WHITE }}>{svc.name} Premium</div>
                <div style={{ fontSize: 26, color: GRAY, marginTop: 4 }}>גישה מיידית · לגיטימי</div>
              </div>
              <div style={{
                fontSize: 34, fontWeight: 900, color: svc.color,
              }}>
                {svc.price}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 4: מפתחות + וריפיקיישן (360-480) ───────────────────────────────────
const SceneKeys: React.FC = () => {
  const frame = useCurrentFrame();

  const items = [
    { icon: "🪟", title: "Windows Activation",  sub: "מפתחות מקוריים",       color: CYAN   },
    { icon: "📦", title: "Microsoft 365",        sub: "Office מלא",           color: GOLD   },
    { icon: "✅", title: "אימות כחול",            sub: "Instagram / TikTok",   color: "#1D9BF0" },
  ];

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", padding: "0 80px" }}>
      <GridBg accent={GOLD} />

      <div style={{ ...fadeUp(frame, 0), fontFamily, textAlign: "center", direction: "rtl", marginBottom: 60 }}>
        <div style={{ fontSize: 36, color: GOLD, fontWeight: 700, letterSpacing: 2, marginBottom: 16 }}>
          עוד שירותים
        </div>
        <div style={{ fontSize: 72, fontWeight: 900, color: WHITE }}>
          הכל במקום אחד
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 28, width: "100%" }}>
        {items.map((item, i) => {
          const prog = ease(frame, i * 18 + 18, i * 18 + 44);
          return (
            <div key={item.title} style={{
              opacity: prog,
              transform: `translateY(${interpolate(prog, [0, 1], [60, 0])}px)`,
              display: "flex",
              alignItems: "center",
              background: `${item.color}12`,
              border: `1.5px solid ${item.color}45`,
              borderRadius: 24,
              padding: "30px 44px",
              gap: 32,
              direction: "rtl",
              fontFamily,
            }}>
              <div style={{ fontSize: 64 }}>{item.icon}</div>
              <div>
                <div style={{ fontSize: 44, fontWeight: 800, color: WHITE }}>{item.title}</div>
                <div style={{ fontSize: 28, color: item.color, marginTop: 6, fontWeight: 600 }}>{item.sub}</div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 5: CTA (480-600) ────────────────────────────────────────────────────
const SceneCTA: React.FC = () => {
  const frame = useCurrentFrame();

  const pulse = Math.sin(frame * 0.08) * 0.04 + 1;
  const lineW = interpolate(frame, [20, 60], [0, 680], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const badges = ["⚡ מהיר", "🔒 אנונימי", "✅ מובטח", "₿ קריפטו"];

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 0 }}>
      <GridBg accent={CYAN} />

      {/* כותרת */}
      <div style={{ ...fadeUp(frame, 0), fontFamily, textAlign: "center", direction: "rtl" }}>
        <div style={{ fontSize: 44, color: CYAN, fontWeight: 700, letterSpacing: 2, marginBottom: 20 }}>
          מוכן להתחיל?
        </div>
        <div style={{
          fontSize: 80, fontWeight: 900, color: WHITE, lineHeight: 1.05,
          textShadow: `0 0 50px ${CYAN}60`,
        }}>
          arel
        </div>
        <div style={{
          fontSize: 80, fontWeight: 900, color: CYAN, lineHeight: 1.05,
          transform: `scale(${pulse})`,
          textShadow: `0 0 40px ${CYAN}`,
        }}>
          arelkohavi.com
        </div>
      </div>

      {/* קו */}
      <div style={{
        width: lineW, height: 2, margin: "40px 0",
        background: `linear-gradient(90deg, transparent, ${CYAN}, transparent)`,
        boxShadow: `0 0 20px ${CYAN}`,
      }} />

      {/* Badges */}
      <div style={{
        ...fadeIn(frame, 35),
        display: "flex", flexWrap: "wrap", justifyContent: "center",
        gap: 20, padding: "0 60px", direction: "rtl",
      }}>
        {badges.map((b, i) => (
          <div key={i} style={{
            background: `${CYAN}18`,
            border: `1.5px solid ${CYAN}50`,
            borderRadius: 999,
            padding: "16px 40px",
            fontSize: 34,
            color: WHITE,
            fontFamily,
            fontWeight: 700,
          }}>
            {b}
          </div>
        ))}
      </div>

      {/* כפתור */}
      <div style={{
        opacity: fadeUp(frame, 55).opacity,
        marginTop: 56,
        background: `linear-gradient(135deg, ${CYAN}, ${PURPLE})`,
        borderRadius: 999,
        padding: "32px 100px",
        fontFamily,
        fontSize: 44,
        fontWeight: 900,
        color: BG,
        boxShadow: `0 0 60px ${CYAN}50`,
        transform: `${fadeUp(frame, 55).transform} scale(${pulse})`,
        direction: "rtl",
      }}>
        צור קשר עכשיו ←
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  ROOT COMPONENT
// ══════════════════════════════════════════════════════════════════════════════
export const ArelKohaviVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: BG, fontFamily }}>
      <Sequence from={0}   durationInFrames={100}><SceneOpening  /></Sequence>
      <Sequence from={100} durationInFrames={130}><SceneUnban    /></Sequence>
      <Sequence from={230} durationInFrames={130}><SceneStreaming /></Sequence>
      <Sequence from={360} durationInFrames={120}><SceneKeys     /></Sequence>
      <Sequence from={480} durationInFrames={120}><SceneCTA      /></Sequence>
    </AbsoluteFill>
  );
};
