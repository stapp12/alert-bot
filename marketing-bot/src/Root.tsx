import { Composition } from "remotion";
import { Video } from "./Video";
import { BoostlyVideo } from "./BoostlyVideo";
import { BoostlyAd } from "./BoostlyAd";
import { HolylandVideo } from "./HolylandVideo";
import { BoostlyDemo } from "./BoostlyDemo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Ad"
        component={Video}
        durationInFrames={300}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ text: "הטקסט שלך כאן" }}
      />
      <Composition
        id="Boostly"
        component={BoostlyVideo}
        durationInFrames={480}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="BoostlyAd"
        component={BoostlyAd}
        durationInFrames={540}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="Holyland"
        component={HolylandVideo}
        durationInFrames={600}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="BoostlyDemo"
        component={BoostlyDemo}
        durationInFrames={450}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
