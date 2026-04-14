import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Easing,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Heebo";

const { fontFamily } = loadFont();

// ── צבעי האתר האמיתיים ────────────────────────────────────────────────────────
const CREAM   = "#F8F4EE";
const GOLD    = "#C9942A";
const GOLD_L  = "#E8B84B";
const BLACK   = "#1A1A1A";
const DARK    = "#2C2C2C";
const GRAY    = "#888";
const WHITE   = "#FFFFFF";
const RED_OFF = "#C0392B";

// ── עזרי אנימציה ─────────────────────────────────────────────────────────────
const eased = (frame: number, from: number, to: number, ease = Easing.out(Easing.cubic)) =>
  interpolate(frame, [from, to], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });

// ══════════════════════════════════════════════════════════════════════════════
//  פריים של טלפון
// ══════════════════════════════════════════════════════════════════════════════
const PHONE_W = 860;
const PHONE_H = 1720;
const RADIUS  = 52;
const BAR_H   = 110;

const PhoneFrame: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div style={{
      position: "absolute",
      width: PHONE_W,
      height: PHONE_H,
      borderRadius: RADIUS,
      overflow: "hidden",
      boxShadow: "0 40px 120px rgba(0,0,0,0.55), 0 0 0 12px #1A1A1A, 0 0 0 14px #333",
      background: WHITE,
    }}>
      {/* Status bar */}
      <div style={{
        height: 52, background: WHITE,
        display: "flex", alignItems: "center",
        justifyContent: "space-between",
        padding: "0 32px", fontSize: 24, color: BLACK, fontWeight: 600,
      }}>
        <span>22:26</span>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <span>📶</span><span>🔋</span>
        </div>
      </div>

      {/* Browser bar */}
      <div style={{
        height: BAR_H, background: WHITE,
        display: "flex", alignItems: "center",
        padding: "0 20px", gap: 16, borderBottom: "1px solid #eee",
      }}>
        <div style={{ fontSize: 32, color: "#555" }}>←</div>
        <div style={{
          flex: 1, height: 58, background: "#F2F2F7",
          borderRadius: 16, display: "flex", alignItems: "center",
          padding: "0 24px", gap: 12,
        }}>
          <div style={{ fontSize: 24, color: "#555" }}>🔒</div>
          <span style={{ fontSize: 26, color: DARK, fontWeight: 500 }}>holylandsecrets.com</span>
        </div>
        <div style={{ fontSize: 32, color: "#555" }}>⊕</div>
      </div>

      {/* Content area */}
      <div style={{
        width: PHONE_W,
        height: PHONE_H - 52 - BAR_H,
        overflow: "hidden",
        position: "relative",
      }}>
        {children}
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  אצבע / קורסור
// ══════════════════════════════════════════════════════════════════════════════
const Finger: React.FC<{ x: number; y: number; visible: boolean; tapping?: boolean }> = ({ x, y, visible, tapping }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = tapping
    ? 1 + 0.3 * Math.sin(interpolate(frame % 10, [0, 10], [0, Math.PI]))
    : 1;
  const opacity = visible ? 1 : 0;

  return (
    <div style={{
      position: "absolute",
      left: x - 30, top: y - 30,
      width: 60, height: 60,
      borderRadius: "50%",
      background: "rgba(0,0,0,0.35)",
      border: "3px solid rgba(255,255,255,0.8)",
      transform: `scale(${scale})`,
      opacity,
      zIndex: 999,
      pointerEvents: "none",
      transition: "opacity 0.2s",
      boxShadow: "0 2px 12px rgba(0,0,0,0.4)",
    }} />
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  רכיבי האתר המדומה
// ══════════════════════════════════════════════════════════════════════════════

// ── Header ───────────────────────────────────────────────────────────────────
const SiteHeader: React.FC = () => (
  <div style={{
    height: 90, background: WHITE,
    display: "flex", alignItems: "center",
    justifyContent: "space-between",
    padding: "0 36px",
    borderBottom: "1px solid #e8e0d5",
  }}>
    <span style={{ fontSize: 38, color: DARK }}>≡</span>
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ fontFamily: "serif", fontSize: 28, color: GOLD, fontWeight: 700, letterSpacing: 1 }}>HolyLand</span>
      <span style={{ fontFamily: "serif", fontSize: 22, color: GOLD, fontStyle: "italic" }}>Secrets</span>
    </div>
    <span style={{ fontSize: 38, color: DARK }}>🛒</span>
  </div>
);

// ── Hero ─────────────────────────────────────────────────────────────────────
const SiteHero: React.FC = () => (
  <div style={{
    background: "linear-gradient(145deg, #F5EFDF, #EDE3CE, #F5EFDF)",
    padding: "60px 40px 80px",
    textAlign: "center",
    direction: "rtl",
    position: "relative",
    overflow: "hidden",
  }}>
    {/* שיש רקע */}
    <div style={{
      position: "absolute", inset: 0, opacity: 0.18,
      backgroundImage: "repeating-linear-gradient(120deg, transparent, transparent 80px, rgba(180,150,80,0.15) 80px, rgba(180,150,80,0.15) 82px)",
    }} />

    {/* מוצרים מדומים */}
    <div style={{
      width: 480, height: 340, margin: "0 auto 40px",
      background: "linear-gradient(135deg, #1A1A1A, #2C2C2C)",
      borderRadius: 24, display: "flex", alignItems: "center",
      justifyContent: "center", fontSize: 80,
      boxShadow: "0 16px 48px rgba(0,0,0,0.3)",
    }}>
      🧴✨💆‍♀️
    </div>

    <h1 style={{
      fontFamily: "serif", fontSize: 68, fontWeight: 900,
      color: GOLD, margin: "0 0 16px", lineHeight: 1.15,
    }}>
      HOLYLAND<br />SECRETS
    </h1>
    <p style={{ fontSize: 42, color: DARK, margin: "0 0 12px", fontWeight: 600 }}>
      אוסף טיפוח השיער האולטימטיבי
    </p>
    <p style={{ fontSize: 32, color: "#666", margin: "0 0 48px", lineHeight: 1.5 }}>
      מוצרים מקצועיים עם שמן קיק וקרטין עשירים<br />
      בשמן טבעי, קולגן וויטמינים
    </p>
    <div style={{
      display: "inline-block",
      background: GOLD,
      borderRadius: 16, padding: "22px 80px",
      fontSize: 42, fontWeight: 700, color: WHITE,
      boxShadow: `0 6px 24px ${GOLD}66`,
    }}>
      ← רכשי עכשיו
    </div>
  </div>
);

// ── Product card ──────────────────────────────────────────────────────────────
const ProductCard: React.FC = () => (
  <div style={{ background: WHITE, padding: "0 0 60px", direction: "rtl" }}>
    {/* קישור חזרה */}
    <div style={{ padding: "20px 36px", fontSize: 28, color: GOLD, borderBottom: "1px solid #f0e8d8" }}>
      → חזרה למוצרים
    </div>

    {/* תמונה ראשית */}
    <div style={{
      background: "#111",
      height: 480,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 100,
    }}>
      🎁
    </div>

    {/* תמונות קטנות */}
    <div style={{ display: "flex", gap: 12, padding: "16px 20px", borderBottom: "1px solid #f0e8d8" }}>
      {["🧴", "🌿", "💧", "🪮"].map((em, i) => (
        <div key={i} style={{
          width: 110, height: 110, borderRadius: 12,
          background: i === 0 ? "#e8d8b8" : "#f5f0e8",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 48, border: i === 0 ? `2px solid ${GOLD}` : "2px solid transparent",
        }}>{em}</div>
      ))}
    </div>

    {/* פרטים */}
    <div style={{ padding: "32px 36px" }}>
      <h2 style={{ fontSize: 46, fontWeight: 800, color: DARK, margin: "0 0 20px", lineHeight: 1.3 }}>
        סט מתנה מקצועי לטיפוח שיער<br />(שמפו, מסכה, סרום ומברשת)
      </h2>

      {/* מחיר */}
      <div style={{ display: "flex", alignItems: "center", gap: 20, margin: "0 0 28px" }}>
        <span style={{
          background: RED_OFF, color: WHITE, borderRadius: 8,
          padding: "6px 20px", fontSize: 28, fontWeight: 700,
        }}>OFF 34%</span>
        <span style={{ fontSize: 34, color: GRAY, textDecoration: "line-through" }}>₪480</span>
        <span style={{ fontSize: 56, fontWeight: 900, color: DARK }}>₪320</span>
      </div>

      {/* תיאור */}
      <p style={{ fontSize: 30, color: "#555", marginBottom: 24, lineHeight: 1.6 }}>
        טיפוח שיער יוקרתי – המתנה המושלמת
      </p>

      {/* וי */}
      {[
        "שמפו עם שמן קיק וקרטין – מנקה בעומק",
        "מסכת שיער – משחזרת ומזינה",
        "מברשת עם טיפולי מקצועי לקרפים",
      ].map((t, i) => (
        <div key={i} style={{ display: "flex", gap: 16, margin: "16px 0", alignItems: "flex-start" }}>
          <span style={{ color: GOLD, fontSize: 32, marginTop: 2 }}>✓</span>
          <span style={{ fontSize: 30, color: DARK, lineHeight: 1.4 }}>{t}</span>
        </div>
      ))}

      {/* משלוח */}
      <div style={{
        background: "#f8f4ee", borderRadius: 16, padding: "20px 24px",
        margin: "28px 0", fontSize: 28, color: "#555", border: "1px solid #e8d8b8",
      }}>
        📦 משלוח אקספרס (עד 10 ימי עסקים) ₪25.00
      </div>

      {/* כפתורים */}
      <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
        <div style={{
          flex: 1, background: GOLD,
          borderRadius: 16, padding: "28px 0",
          textAlign: "center", fontSize: 40, fontWeight: 800,
          color: WHITE, boxShadow: `0 6px 24px ${GOLD}55`,
        }}>
          🛒 קנה עכשיו
        </div>
        <div style={{
          width: 180, borderRadius: 16, padding: "28px 0",
          textAlign: "center", fontSize: 32, fontWeight: 600,
          color: GOLD, border: `2px solid ${GOLD}`,
        }}>
          הוסף לסל
        </div>
      </div>
    </div>
  </div>
);

// ── Cart added ────────────────────────────────────────────────────────────────
const CartAdded: React.FC<{ progress: number }> = ({ progress }) => {
  const scale   = interpolate(progress, [0, 0.4, 1], [0.7, 1.08, 1]);
  const opacity = interpolate(progress, [0, 0.2], [0, 1]);
  return (
    <div style={{
      position: "absolute", inset: 0,
      background: "rgba(0,0,0,0.55)",
      display: "flex", alignItems: "center", justifyContent: "center",
      opacity,
    }}>
      <div style={{
        background: WHITE, borderRadius: 32, padding: "56px 72px",
        textAlign: "center", direction: "rtl",
        transform: `scale(${scale})`,
        boxShadow: "0 20px 60px rgba(0,0,0,0.4)",
        maxWidth: 640,
      }}>
        <div style={{ fontSize: 100, marginBottom: 20 }}>✅</div>
        <div style={{ fontSize: 48, fontWeight: 800, color: DARK, marginBottom: 12 }}>
          נוסף לסל בהצלחה!
        </div>
        <div style={{ fontSize: 32, color: GRAY, marginBottom: 36 }}>
          סט מתנה מקצועי לטיפוח שיער
        </div>
        <div style={{
          background: GOLD, borderRadius: 14, padding: "22px 56px",
          fontSize: 38, fontWeight: 700, color: WHITE,
          boxShadow: `0 6px 20px ${GOLD}55`,
        }}>
          ← המשך לתשלום
        </div>
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  סצנה אחרונה — CTA חיצוני
// ══════════════════════════════════════════════════════════════════════════════
const FinalCTA: React.FC<{ progress: number }> = ({ progress }) => {
  const scale = interpolate(progress, [0, 1], [0.85, 1]);
  const op    = interpolate(progress, [0, 0.3], [0, 1]);
  const pulse = 1 + 0.03 * Math.sin(progress * Math.PI * 6);

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(160deg, #1A1A1A, #2d1f00)`,
      justifyContent: "center", alignItems: "center", flexDirection: "column",
      gap: 40, opacity: op, direction: "rtl",
    }}>
      <div style={{
        position: "absolute", width: 800, height: 800,
        borderRadius: "50%",
        background: `radial-gradient(circle, ${GOLD}25 0%, transparent 65%)`,
      }} />

      <div style={{ transform: `scale(${scale})`, textAlign: "center" }}>
        <div style={{ fontSize: 52, color: GOLD_L, marginBottom: 8, fontStyle: "italic", fontFamily: "serif" }}>
          HolyLand Secrets
        </div>
        <div style={{ fontSize: 78, fontWeight: 900, color: WHITE, lineHeight: 1.2, marginBottom: 24 }}>
          השיער שלך<br />מגיע לטוב ביותר
        </div>
        <div style={{ fontSize: 38, color: "#ccc", marginBottom: 48 }}>
          OFF 34% · ₪320 בלבד · משלוח מהיר
        </div>
      </div>

      <div style={{
        transform: `scale(${pulse})`,
        background: `linear-gradient(135deg, ${GOLD}, #E8B84B)`,
        borderRadius: 999, padding: "30px 90px",
        fontSize: 48, fontWeight: 800, color: "#1A1A1A",
        boxShadow: `0 10px 40px ${GOLD}66`,
      }}>
        ⚡ holylandsecrets.com
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
//  קומפוזיציה ראשית
// ══════════════════════════════════════════════════════════════════════════════
export const HolylandVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // ── כניסת הטלפון (0-35) ───────────────────────────────────────────────────
  const phoneEntry  = spring({ fps, frame, config: { damping: 16, stiffness: 80 } });
  const phoneScale  = interpolate(phoneEntry, [0, 1], [0.7, 1]);
  const phoneOp     = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });

  // ── גלילה: Hero → Product (50-210) ───────────────────────────────────────
  const scrollProg = eased(frame, 55, 200, Easing.inOut(Easing.cubic));
  const heroHeight = 740; // גובה ה-Hero
  const scrollY    = interpolate(scrollProg, [0, 1], [0, heroHeight]);

  // ── אצבע: מחכה → לוחצת על קנה עכשיו (220-290) ────────────────────────────
  const fingerVisible = frame >= 210 && frame <= 340;
  // אצבע נעה לכפתור
  const fingerMoveProg = eased(frame, 215, 250);
  const fingerX = interpolate(fingerMoveProg, [0, 1], [430, 320]);
  const fingerY = interpolate(fingerMoveProg, [0, 1], [900, 1120]);
  const isTapping = frame >= 255 && frame <= 290;

  // ── ripple על כפתור (255-310) ─────────────────────────────────────────────
  const rippleProg   = eased(frame, 255, 310);
  const rippleScale  = interpolate(rippleProg, [0, 1], [0, 3.5]);
  const rippleOp     = interpolate(rippleProg, [0, 0.6, 1], [0.6, 0.3, 0]);

  // ── פופאפ הוסף לסל (295-400) ──────────────────────────────────────────────
  const cartProg = eased(frame, 295, 360);

  // ── CTA סופי (430-600) ────────────────────────────────────────────────────
  const showFinal   = frame >= 415;
  const finalProg   = eased(frame, 415, 470);
  const phoneExitOp = interpolate(frame, [405, 430], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{
      background: "linear-gradient(160deg, #0d0d0d, #1a1500)",
      fontFamily,
      justifyContent: "center",
      alignItems: "center",
    }}>
      {/* רקע זהוב עדין */}
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse at 50% 50%, ${GOLD}12 0%, transparent 60%)`,
      }} />

      {/* טלפון */}
      {!showFinal && (
        <div style={{
          transform: `scale(${phoneScale})`,
          opacity: phoneOp * phoneExitOp,
          position: "relative",
          width: PHONE_W,
          height: PHONE_H,
        }}>
          <PhoneFrame>
            {/* תוכן האתר עם גלילה */}
            <div style={{
              position: "absolute",
              top: -scrollY,
              width: "100%",
              transition: "none",
            }}>
              <SiteHeader />
              <SiteHero />
              <ProductCard />
            </div>

            {/* Ripple על כפתור "קנה עכשיו" */}
            {frame >= 255 && frame <= 310 && (
              <div style={{
                position: "absolute",
                left: 125, top: 920,
                width: 500, height: 100,
                display: "flex", alignItems: "center", justifyContent: "center",
                overflow: "visible",
                pointerEvents: "none",
              }}>
                <div style={{
                  width: 300, height: 300,
                  borderRadius: "50%",
                  background: "rgba(255,255,255,0.4)",
                  transform: `scale(${rippleScale})`,
                  opacity: rippleOp,
                  position: "absolute",
                }} />
              </div>
            )}

            {/* פופאפ הוסף לסל */}
            {frame >= 295 && <CartAdded progress={cartProg} />}

            {/* אצבע */}
            <Finger
              x={fingerX - (PHONE_W - 860) / 2}
              y={fingerY}
              visible={fingerVisible}
              tapping={isTapping}
            />
          </PhoneFrame>
        </div>
      )}

      {/* CTA סופי */}
      {showFinal && <FinalCTA progress={finalProg} />}
    </AbsoluteFill>
  );
};
