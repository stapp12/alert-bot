import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const MESSAGES = [
  "מוצר מדהים",
  "מחיר שאי אפשר לסרב לו",
  "משלוח חינם",
  "הזמינו עכשיו!",
];

const TextSlide: React.FC<{ text: string; startFrame: number }> = ({
  text,
  startFrame,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const localFrame = frame - startFrame;
  const slideInProgress = spring({ fps, frame: localFrame, config: { damping: 14, stiffness: 120 } });
  const opacity = interpolate(localFrame, [0, 10, 40, 50], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(slideInProgress, [0, 1], [60, 0]);

  if (localFrame < 0 || localFrame > 50) return null;

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px)`,
        fontSize: 72,
        fontWeight: 900,
        color: "#fff",
        textAlign: "center",
        textShadow: "0 4px 24px rgba(0,0,0,0.5)",
        padding: "0 40px",
        letterSpacing: 2,
        direction: "rtl",
      }}
    >
      {text}
    </div>
  );
};

export const MarketingVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();

  const bgHue = interpolate(frame, [0, 150], [220, 280], {
    extrapolateRight: "clamp",
  });

  const pulseScale = 1 + 0.015 * Math.sin((frame / fps) * Math.PI * 2);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, hsl(${bgHue}, 80%, 30%), hsl(${bgHue + 40}, 90%, 15%))`,
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 32,
      }}
    >
      {/* Logo / brand circle */}
      <div
        style={{
          width: 120,
          height: 120,
          borderRadius: "50%",
          background: "rgba(255,255,255,0.15)",
          border: "3px solid rgba(255,255,255,0.4)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 48,
          transform: `scale(${pulseScale})`,
          marginBottom: 16,
        }}
      >
        🚀
      </div>

      {/* Animated text slides */}
      <div style={{ height: 120, display: "flex", alignItems: "center", justifyContent: "center" }}>
        {MESSAGES.map((msg, i) => (
          <div key={i} style={{ position: "absolute" }}>
            <TextSlide text={msg} startFrame={i * 37} />
          </div>
        ))}
      </div>

      {/* Progress bar */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          width: "60%",
          height: 6,
          background: "rgba(255,255,255,0.2)",
          borderRadius: 999,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            background: "rgba(255,255,255,0.85)",
            borderRadius: 999,
            width: `${interpolate(frame, [0, 148], [0, 100], { extrapolateRight: "clamp" })}%`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
