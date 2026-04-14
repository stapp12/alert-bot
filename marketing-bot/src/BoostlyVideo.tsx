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
const BG       = "#0A0A1A";
const PURPLE   = "#7C3AED";
const PURPLE_L = "#A78BFA";
const GOLD     = "#F59E0B";
const WHITE    = "#FFFFFF";
const GRAY     = "rgba(255,255,255,0.65)";

// ── עזרים ─────────────────────────────────────────────────────────────────────
const useFadeSlide = (startFrame: number, dir: "up" | "down" | "left" = "up") => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame - startFrame;
  const prog  = spring({ fps, frame: local, config: { damping: 16, stiffness: 100 } });
  const opacity = interpolate(local, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const dist = 60;
  const translate = interpolate(prog, [0, 1], [dist, 0]);
  const transform =
    dir === "up"   ? `translateY(${translate}px)` :
    dir === "down" ? `translateY(-${translate}px)` :
                     `translateX(${translate}px)`;
  return { opacity, transform };
};

// ── Pill (label קטן) ──────────────────────────────────────────────────────────
const Pill: React.FC<{ text: string; color?: string }> = ({ text, color = PURPLE }) => (
  <div style={{
    background: `${color}33`,
    border: `1.5px solid ${color}`,
    borderRadius: 999,
    padding: "10px 32px",
    fontSize: 32,
    color,
    fontWeight: 700,
    display: "inline-block",
  }}>
    {text}
  </div>
);

// ══════════════════════════════════════════════════════════════════════════════
//  סצנה 1 — פתיחה (0-90)
// ══════════════════════════════════════════════════════════════════════════════
const SceneOpening: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ fps, frame, config: { damping: 14, stiffness: 90 } });
  const logoS     = interpolate(logoScale, [0, 1], [0.4, 1]);
  const logoOp    = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  const tagline = useFadeSlide(20, "up");
  const pill    = useFadeSlide(35, "up");

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 36 }}>
      {/* Glow */}
      <div style={{
        position: "absolute", width: 700, height: 700, borderRadius: "50%",
        background: `radial-gradient(circle, ${PURPLE}30 0%, transparent 70%)`,
        top: "50%", left: "50%", transform: "translate(-50%, -50%)",
      }} />

      {/* לוגו */}
      <div style={{ opacity: logoOp, transform: `scale(${logoS})`, textAlign: "center" }}>
        <div style={{
          fontSize: 110, fontWeight: 900, color: WHITE, letterSpacing: -2,
          textShadow: `0 0 40px ${PURPLE}`,
        }}>
          Boostly
        </div>
        <div style={{ width: 160, height: 4, background: `linear-gradient(90deg, transparent, ${GOLD}, transparent)`, margin: "12px auto 0" }} />
      </div>

      {/* סלוגן */}
      <div style={{ ...tagline, textAlign: "center", fontSize: 46, color: GRAY, maxWidth: 780, lineHeight: 1.4, direction: "rtl" }}>
        הפלטפורמה המובילה לשיווק ברשתות חברתיות
      </div>

      {/* תג */}
      <div style={pill}>
        <Pill text="🇮🇱 המחיר הזול ביותר בישראל" color={GOLD} />
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  סצנה 2 — פלטפורמות (90-195)
// ══════════════════════════════════════════════════════════════════════════════
const PLATFORMS = [
  { icon: "📸", name: "אינסטגרם", color: "#E1306C" },
  { icon: "🎵", name: "טיקטוק",   color: "#69C9D0" },
  { icon: "📘", name: "פייסבוק",  color: "#1877F2" },
  { icon: "▶️", name: "יוטיוב",   color: "#FF0000" },
];

const PlatformCard: React.FC<{ icon: string; name: string; color: string; delay: number }> = ({ icon, name, color, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame - delay;
  const prog  = spring({ fps, frame: local, config: { damping: 14, stiffness: 110 } });
  const scale   = interpolate(prog, [0, 1], [0.5, 1]);
  const opacity = interpolate(local, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div style={{
      opacity, transform: `scale(${scale})`,
      background: `${color}18`,
      border: `2px solid ${color}55`,
      borderRadius: 32,
      width: 220, height: 220,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      gap: 14,
    }}>
      <div style={{ fontSize: 72 }}>{icon}</div>
      <div style={{ fontSize: 38, fontWeight: 700, color: WHITE }}>{name}</div>
    </div>
  );
};

const ScenePlatforms: React.FC = () => {
  const title = useFadeSlide(0, "down");
  const services = useFadeSlide(25, "up");

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 56 }}>
      <div style={{ ...title, fontSize: 60, fontWeight: 900, color: WHITE, textAlign: "center", direction: "rtl" }}>
        ✨ כל הפלטפורמות במקום אחד
      </div>

      <div style={{ display: "flex", gap: 28, flexWrap: "wrap", justifyContent: "center" }}>
        {PLATFORMS.map((p, i) => (
          <PlatformCard key={p.name} {...p} delay={10 + i * 12} />
        ))}
      </div>

      <div style={{ ...services, textAlign: "center", direction: "rtl" }}>
        <div style={{ fontSize: 40, color: GRAY }}>
          עוקבים · לייקים · צפיות · תגובות
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  סצנה 3 — 3 שלבים (195-390)
// ══════════════════════════════════════════════════════════════════════════════
const STEPS = [
  {
    num: "01",
    icon: "👤",
    title: "צור חשבון חינמי",
    desc: "הרשמה מהירה + טעינת יתרה\n5% בונוס על כל טעינה!",
    color: PURPLE,
  },
  {
    num: "02",
    icon: "🎯",
    title: "בחר שירות",
    desc: "פלטפורמה · סוג שירות · כמות\nמחירים נמוכים במיוחד",
    color: "#06B6D4",
  },
  {
    num: "03",
    icon: "🚀",
    title: "קבל תוצאות",
    desc: "ההזמנה מתחילה אוטומטית\nתוצאות תוך דקות!",
    color: GOLD,
  },
];

const StepCard: React.FC<typeof STEPS[0] & { delay: number }> = ({ num, icon, title, desc, color, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame - delay;
  const prog  = spring({ fps, frame: local, config: { damping: 14, stiffness: 90 } });
  const translateX = interpolate(prog, [0, 1], [-120, 0]);
  const opacity    = interpolate(local, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div style={{
      opacity, transform: `translateX(${translateX}px)`,
      background: "rgba(255,255,255,0.04)",
      border: `2px solid ${color}44`,
      borderRadius: 32,
      padding: "36px 44px",
      display: "flex", alignItems: "center", gap: 36,
      width: 900,
      direction: "rtl",
    }}>
      {/* מספר */}
      <div style={{
        width: 90, height: 90, borderRadius: "50%",
        background: `${color}22`,
        border: `2.5px solid ${color}`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 36, fontWeight: 900, color, flexShrink: 0,
      }}>
        {num}
      </div>

      {/* אייקון + טקסט */}
      <div style={{ display: "flex", alignItems: "center", gap: 24, flex: 1 }}>
        <div style={{ fontSize: 64 }}>{icon}</div>
        <div>
          <div style={{ fontSize: 46, fontWeight: 800, color: WHITE, marginBottom: 8 }}>{title}</div>
          <div style={{ fontSize: 34, color: GRAY, whiteSpace: "pre-line", lineHeight: 1.5 }}>{desc}</div>
        </div>
      </div>
    </div>
  );
};

const SceneSteps: React.FC = () => {
  const title = useFadeSlide(0, "down");

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 40 }}>
      <div style={{ ...title, fontSize: 62, fontWeight: 900, color: WHITE, direction: "rtl", marginBottom: 12 }}>
        3 שלבים פשוטים 👇
      </div>
      {STEPS.map((s, i) => (
        <StepCard key={s.num} {...s} delay={15 + i * 30} />
      ))}
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  סצנה 4 — CTA (390-480)
// ══════════════════════════════════════════════════════════════════════════════
const SceneCTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const title   = useFadeSlide(0, "down");
  const sub     = useFadeSlide(15, "up");
  const bonus   = useFadeSlide(25, "up");
  const url     = useFadeSlide(38, "up");

  const pulse = 1 + 0.04 * Math.sin((frame / fps) * Math.PI * 3);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 44 }}>
      {/* גלו */}
      <div style={{
        position: "absolute", width: 800, height: 800, borderRadius: "50%",
        background: `radial-gradient(circle, ${GOLD}20 0%, transparent 65%)`,
        top: "50%", left: "50%", transform: "translate(-50%, -50%)",
      }} />

      <div style={{ ...title, fontSize: 80, fontWeight: 900, color: WHITE, textAlign: "center", direction: "rtl", lineHeight: 1.2 }}>
        מוכן להגדיל<br />את הנוכחות שלך?
      </div>

      <div style={{ ...sub, fontSize: 46, color: GRAY, textAlign: "center", direction: "rtl" }}>
        הרשמה חינמית · ללא התחייבות
      </div>

      {/* בונוס */}
      <div style={{ ...bonus }}>
        <div style={{
          background: `linear-gradient(135deg, ${GOLD}, #F97316)`,
          borderRadius: 999,
          padding: "22px 60px",
          fontSize: 44,
          fontWeight: 800,
          color: "#0A0A1A",
          direction: "rtl",
          boxShadow: `0 8px 32px ${GOLD}50`,
        }}>
          🎁 5% בונוס על כל טעינה ראשונה
        </div>
      </div>

      {/* כתובת */}
      <div style={{ ...url, transform: `${url.transform} scale(${pulse})` }}>
        <div style={{
          background: `linear-gradient(135deg, ${PURPLE}, #6366F1)`,
          borderRadius: 999,
          padding: "28px 80px",
          fontSize: 50,
          fontWeight: 900,
          color: WHITE,
          letterSpacing: 1,
          boxShadow: `0 8px 40px ${PURPLE}60`,
        }}>
          ⚡ boostlyshop.com
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  קומפוזיציה ראשית
// ══════════════════════════════════════════════════════════════════════════════
export const BoostlyVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: BG, fontFamily, direction: "rtl" }}>

      {/* רקע נקודות */}
      <AbsoluteFill style={{
        backgroundImage: `radial-gradient(circle, rgba(124,58,237,0.15) 1px, transparent 1px)`,
        backgroundSize: "60px 60px",
      }} />

      <Sequence from={0}   durationInFrames={90}>  <SceneOpening />  </Sequence>
      <Sequence from={90}  durationInFrames={105}> <ScenePlatforms /></Sequence>
      <Sequence from={195} durationInFrames={195}> <SceneSteps />    </Sequence>
      <Sequence from={390} durationInFrames={90}>  <SceneCTA />      </Sequence>
    </AbsoluteFill>
  );
};
