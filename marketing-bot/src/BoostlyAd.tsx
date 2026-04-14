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

// ── צבעים ──────────────────────────────────────────────────────────────────
const BG      = "#07071A";
const PURPLE  = "#8B5CF6";
const CYAN    = "#06B6D4";
const GOLD    = "#FBBF24";
const GREEN   = "#10B981";
const WHITE   = "#FFFFFF";
const GRAY    = "rgba(255,255,255,0.6)";
const CARD_BG = "rgba(255,255,255,0.05)";

// ── Spring helper ──────────────────────────────────────────────────────────
const useSpring = (start: number, cfg = { damping: 14, stiffness: 100 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ fps, frame: frame - start, config: cfg });
};

const useFade = (start: number, dur = 10) => {
  const frame = useCurrentFrame();
  return interpolate(frame - start, [0, dur], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
};

// ══════════════════════════════════════════════════════════════════════════
//  סצנה 1 — Hook (0-75)  "5000 עוקבים תוך 48 שעות"
// ══════════════════════════════════════════════════════════════════════════
const SceneHook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // מונה עולה מ-0 ל-5000
  const counterProg = interpolate(frame, [10, 70], [0, 5000], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
    easing: (t) => 1 - Math.pow(1 - t, 3),
  });
  const count = Math.floor(counterProg);

  const scaleIn = spring({ fps, frame, config: { damping: 12, stiffness: 80 } });
  const labelScale = interpolate(scaleIn, [0, 1], [0.3, 1]);
  const labelOp = useFade(0, 15);

  const subOp   = useFade(20, 10);
  const tagOp   = useFade(38, 10);
  const tagProg = spring({ fps, frame: frame - 38, config: { damping: 14, stiffness: 100 } });
  const tagY    = interpolate(tagProg, [0, 1], [40, 0]);

  // פולס על המונה
  const pulse = 1 + 0.03 * Math.sin((frame / fps) * Math.PI * 8);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 32 }}>
      {/* רקע glow */}
      <div style={{
        position: "absolute", width: 900, height: 900, borderRadius: "50%",
        background: `radial-gradient(circle, ${PURPLE}25 0%, transparent 65%)`,
        top: "50%", left: "50%", transform: "translate(-50%,-55%)",
      }} />

      {/* לוגו */}
      <div style={{
        opacity: labelOp, transform: `scale(${labelScale})`,
        fontSize: 52, fontWeight: 900, color: GRAY, letterSpacing: 4,
        textTransform: "uppercase",
      }}>
        BOOSTLY
      </div>

      {/* מונה */}
      <div style={{
        transform: `scale(${pulse})`,
        fontSize: 160, fontWeight: 900,
        background: `linear-gradient(135deg, ${PURPLE}, ${CYAN})`,
        WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
        lineHeight: 1, fontVariantNumeric: "tabular-nums",
        textAlign: "center",
      }}>
        {count.toLocaleString()}
      </div>

      {/* עוקבים */}
      <div style={{
        opacity: subOp, fontSize: 58, fontWeight: 800,
        color: WHITE, direction: "rtl", textAlign: "center",
      }}>
        👥 עוקבים חדשים
      </div>

      {/* תג זמן */}
      <div style={{
        opacity: tagOp, transform: `translateY(${tagY}px)`,
        background: `linear-gradient(135deg, ${GOLD}, #F97316)`,
        borderRadius: 999, padding: "18px 52px",
        fontSize: 44, fontWeight: 800, color: "#0A0A1A",
        direction: "rtl",
      }}>
        ⚡ תוך 48 שעות בלבד
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════
//  סצנה 2 — השוואת מחירים (75-185)
// ══════════════════════════════════════════════════════════════════════════
const COMPARE = [
  { label: "המתחרים", price: "₪180", color: "#EF4444", cross: true },
  { label: "Boostly", price: "₪39",  color: GREEN,      cross: false, best: true },
];

const PriceCard: React.FC<{ label: string; price: string; color: string; cross: boolean; best?: boolean; delay: number }> =
  ({ label, price, color, cross, best, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const prog  = spring({ fps, frame: frame - delay, config: { damping: 13, stiffness: 90 } });
  const scale = interpolate(prog, [0, 1], [0.5, 1]);
  const op    = interpolate(frame - delay, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div style={{
      opacity: op, transform: `scale(${scale})`,
      background: best ? `${color}18` : CARD_BG,
      border: `3px solid ${color}`,
      borderRadius: 36,
      padding: "44px 56px",
      display: "flex", flexDirection: "column",
      alignItems: "center", gap: 20,
      minWidth: 380,
      position: "relative",
    }}>
      {best && (
        <div style={{
          position: "absolute", top: -24,
          background: `linear-gradient(90deg, ${GREEN}, #059669)`,
          borderRadius: 999, padding: "8px 28px",
          fontSize: 30, fontWeight: 800, color: WHITE,
        }}>
          🏆 הזול ביותר
        </div>
      )}
      <div style={{ fontSize: 42, fontWeight: 700, color: WHITE, direction: "rtl" }}>{label}</div>
      <div style={{
        fontSize: 96, fontWeight: 900, color,
        textDecoration: cross ? "line-through" : "none",
        opacity: cross ? 0.6 : 1,
      }}>
        {price}
      </div>
      <div style={{ fontSize: 34, color: GRAY, direction: "rtl" }}>לכל 1,000 עוקבים</div>
    </div>
  );
};

const ScenePrice: React.FC = () => {
  const titleOp = useFade(0, 12);
  const titleProg = useSpring(0, { damping: 14, stiffness: 90 });
  const titleY = interpolate(titleProg, [0, 1], [-50, 0]);

  const saveProg = useSpring(60, { damping: 13, stiffness: 100 });
  const saveScale = interpolate(saveProg, [0, 1], [0.3, 1]);
  const saveOp = useFade(60, 12);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 60 }}>
      <div style={{
        opacity: titleOp, transform: `translateY(${titleY}px)`,
        fontSize: 62, fontWeight: 900, color: WHITE,
        direction: "rtl", textAlign: "center",
      }}>
        💰 למה לשלם יותר?
      </div>

      <div style={{ display: "flex", gap: 40, alignItems: "center" }}>
        {COMPARE.map((c, i) => <PriceCard key={c.label} {...c} delay={12 + i * 20} />)}
      </div>

      <div style={{
        opacity: saveOp, transform: `scale(${saveScale})`,
        background: `linear-gradient(135deg, ${GOLD}, #F97316)`,
        borderRadius: 999, padding: "22px 60px",
        fontSize: 46, fontWeight: 900, color: "#0A0A1A",
        direction: "rtl",
      }}>
        🎁 חסוך 78% היום!
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════
//  סצנה 3 — שירותים (185-310)
// ══════════════════════════════════════════════════════════════════════════
const SERVICES = [
  { icon: "📸", name: "אינסטגרם", items: ["עוקבים", "לייקים", "צפיות"], color: "#E1306C" },
  { icon: "🎵", name: "טיקטוק",   items: ["עוקבים", "לייקים", "שיתופים"], color: "#69C9D0" },
  { icon: "📘", name: "פייסבוק",  items: ["עוקבים", "לייקים", "צפיות"], color: "#1877F2" },
  { icon: "▶️", name: "יוטיוב",   items: ["צפיות", "מנויים", "לייקים"], color: "#FF0000" },
];

const ServiceCard: React.FC<typeof SERVICES[0] & { delay: number }> = ({ icon, name, items, color, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame - delay;
  const prog  = spring({ fps, frame: local, config: { damping: 13, stiffness: 100 } });
  const translateY = interpolate(prog, [0, 1], [80, 0]);
  const op = interpolate(local, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div style={{
      opacity: op, transform: `translateY(${translateY}px)`,
      background: `${color}12`,
      border: `2px solid ${color}50`,
      borderRadius: 28, padding: "32px 36px",
      display: "flex", flexDirection: "column",
      alignItems: "center", gap: 16,
      width: 230,
    }}>
      <div style={{ fontSize: 60 }}>{icon}</div>
      <div style={{ fontSize: 36, fontWeight: 800, color: WHITE }}>{name}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%" }}>
        {items.map(item => (
          <div key={item} style={{
            fontSize: 28, color: GRAY, direction: "rtl",
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <span style={{ color: GREEN, fontSize: 24 }}>✓</span> {item}
          </div>
        ))}
      </div>
    </div>
  );
};

const SceneServices: React.FC = () => {
  const titleOp = useFade(0, 12);
  const titleProg = useSpring(0);
  const titleY = interpolate(titleProg, [0, 1], [-40, 0]);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 48 }}>
      <div style={{
        opacity: titleOp, transform: `translateY(${titleY}px)`,
        fontSize: 60, fontWeight: 900, color: WHITE,
        direction: "rtl", textAlign: "center",
      }}>
        ✨ כל הפלטפורמות
      </div>

      <div style={{ display: "flex", gap: 24, flexWrap: "wrap", justifyContent: "center" }}>
        {SERVICES.map((s, i) => (
          <ServiceCard key={s.name} {...s} delay={12 + i * 15} />
        ))}
      </div>

      <div style={{ opacity: useFade(80, 12), fontSize: 38, color: GRAY, direction: "rtl", textAlign: "center" }}>
        תוצאות מיידיות · אספקה מהירה · תמיכה 24/7
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════
//  סצנה 4 — Social Proof (310-420)
// ══════════════════════════════════════════════════════════════════════════
const REVIEWS = [
  { name: "דניאל כ.", text: "הזמנתי 5,000 עוקבים — הגיעו תוך יום! 🔥", stars: 5 },
  { name: "מיכל ר.", text: "הכי זול שמצאתי באינטרנט, ואיכות מעולה", stars: 5 },
  { name: "יוסי ב.", text: "שירות מהיר ומקצועי, ממליץ בחום", stars: 5 },
];

const ReviewCard: React.FC<typeof REVIEWS[0] & { delay: number }> = ({ name, text, stars, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame - delay;
  const prog  = spring({ fps, frame: local, config: { damping: 14, stiffness: 90 } });
  const x  = interpolate(prog, [0, 1], [120, 0]);
  const op = interpolate(local, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div style={{
      opacity: op, transform: `translateX(${x}px)`,
      background: CARD_BG,
      border: `1.5px solid rgba(255,255,255,0.1)`,
      borderRadius: 28, padding: "32px 40px",
      direction: "rtl", width: 860,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16, alignItems: "center" }}>
        <div style={{ fontSize: 36, fontWeight: 700, color: WHITE }}>{name}</div>
        <div style={{ fontSize: 34, color: GOLD }}>{"⭐".repeat(stars)}</div>
      </div>
      <div style={{ fontSize: 34, color: GRAY, lineHeight: 1.5 }}>{text}</div>
    </div>
  );
};

const SceneProof: React.FC = () => {
  const titleOp = useFade(0, 12);
  const statsProg = useSpring(70);
  const statsScale = interpolate(statsProg, [0, 1], [0.5, 1]);
  const statsOp = useFade(70, 12);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 36 }}>
      <div style={{
        opacity: titleOp,
        fontSize: 58, fontWeight: 900, color: WHITE,
        direction: "rtl", textAlign: "center",
      }}>
        🌟 לקוחות מרוצים
      </div>

      {REVIEWS.map((r, i) => (
        <ReviewCard key={r.name} {...r} delay={12 + i * 18} />
      ))}

      {/* מספרים */}
      <div style={{
        opacity: statsOp, transform: `scale(${statsScale})`,
        display: "flex", gap: 48, marginTop: 8,
      }}>
        {[
          { num: "50K+", label: "לקוחות מרוצים" },
          { num: "2M+",  label: "הזמנות בוצעו" },
          { num: "99%",  label: "שביעות רצון" },
        ].map(s => (
          <div key={s.label} style={{ textAlign: "center" }}>
            <div style={{ fontSize: 56, fontWeight: 900, color: PURPLE }}>{s.num}</div>
            <div style={{ fontSize: 28, color: GRAY, direction: "rtl" }}>{s.label}</div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════
//  סצנה 5 — CTA (420-540)
// ══════════════════════════════════════════════════════════════════════════
const SceneCTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const title1Op = useFade(0, 12);
  const title1Prog = useSpring(0);
  const title1Y = interpolate(title1Prog, [0, 1], [-60, 0]);

  const bonusProg = useSpring(25, { damping: 12, stiffness: 80 });
  const bonusScale = interpolate(bonusProg, [0, 1], [0.3, 1]);
  const bonusOp = useFade(25, 12);

  const urlProg = useSpring(45, { damping: 10, stiffness: 70 });
  const urlScale = interpolate(urlProg, [0, 1], [0.2, 1]);
  const urlOp = useFade(45, 12);

  const pulse = 1 + 0.05 * Math.sin((frame / fps) * Math.PI * 2.5);
  const glowPulse = 0.5 + 0.5 * Math.sin((frame / fps) * Math.PI * 2);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 48 }}>
      {/* glow */}
      <div style={{
        position: "absolute", width: 1000, height: 1000, borderRadius: "50%",
        background: `radial-gradient(circle, ${PURPLE}${Math.floor(20 + glowPulse * 15).toString(16)} 0%, transparent 60%)`,
        top: "50%", left: "50%", transform: "translate(-50%,-50%)",
      }} />

      <div style={{
        opacity: title1Op, transform: `translateY(${title1Y}px)`,
        fontSize: 78, fontWeight: 900, color: WHITE,
        direction: "rtl", textAlign: "center", lineHeight: 1.25,
      }}>
        מוכן לצמוח?<br />
        <span style={{ color: PURPLE }}>הצטרף עכשיו</span>
      </div>

      {/* בונוס */}
      <div style={{ opacity: bonusOp, transform: `scale(${bonusScale})` }}>
        <div style={{
          background: `linear-gradient(135deg, ${GOLD}, #F97316)`,
          borderRadius: 999, padding: "24px 64px",
          fontSize: 46, fontWeight: 900, color: "#07071A",
          direction: "rtl",
          boxShadow: `0 12px 48px ${GOLD}60`,
        }}>
          🎁 5% בונוס על הטעינה הראשונה
        </div>
      </div>

      {/* כתובת */}
      <div style={{ opacity: urlOp, transform: `scale(${urlScale * pulse})` }}>
        <div style={{
          background: `linear-gradient(135deg, ${PURPLE}, ${CYAN})`,
          borderRadius: 999, padding: "32px 88px",
          fontSize: 54, fontWeight: 900, color: WHITE,
          boxShadow: `0 12px 60px ${PURPLE}80`,
          letterSpacing: 1,
        }}>
          ⚡ boostlyshop.com
        </div>
      </div>

      {/* הרשמה חינמית */}
      <div style={{ opacity: useFade(65, 10), fontSize: 38, color: GRAY, direction: "rtl" }}>
        הרשמה חינמית · ללא התחייבות · תוצאות מיידיות
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════
//  קומפוזיציה ראשית — 540 פריימים = 18 שניות
// ══════════════════════════════════════════════════════════════════════════
export const BoostlyAd: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: BG, fontFamily, direction: "rtl" }}>

      {/* רקע — נקודות */}
      <AbsoluteFill style={{
        backgroundImage: `radial-gradient(circle, rgba(139,92,246,0.12) 1px, transparent 1px)`,
        backgroundSize: "55px 55px",
      }} />

      {/* קו תחתון — progress bar */}
      <ProgressBar total={540} color={PURPLE} />

      <Sequence from={0}   durationInFrames={75}>  <SceneHook />     </Sequence>
      <Sequence from={75}  durationInFrames={110}> <ScenePrice />    </Sequence>
      <Sequence from={185} durationInFrames={125}> <SceneServices /> </Sequence>
      <Sequence from={310} durationInFrames={110}> <SceneProof />    </Sequence>
      <Sequence from={420} durationInFrames={120}> <SceneCTA />      </Sequence>

    </AbsoluteFill>
  );
};

// ── Progress Bar ─────────────────────────────────────────────────────────────
const ProgressBar: React.FC<{ total: number; color: string }> = ({ total, color }) => {
  const frame = useCurrentFrame();
  const pct = Math.min(frame / total, 1) * 100;
  return (
    <div style={{
      position: "absolute", bottom: 0, left: 0,
      width: `${pct}%`, height: 6,
      background: `linear-gradient(90deg, ${color}, ${CYAN})`,
      zIndex: 100,
    }} />
  );
};
