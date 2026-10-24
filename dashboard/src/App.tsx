import { Nav } from "./components/Nav";
import { Hero } from "./components/sections/Hero";
import { Problem } from "./components/sections/Problem";
import { PhysicsEngine } from "./components/sections/PhysicsEngine";
import { AIPipeline } from "./components/sections/AIPipeline";
import { Intervention } from "./components/sections/Intervention";
import { Scale } from "./components/sections/Scale";
import { KeyResults } from "./components/sections/KeyResults";
import { Evaluation } from "./components/sections/Evaluation";
import { FlightReplay } from "./components/sections/FlightReplay";
import { Simulator } from "./components/sections/Simulator";
import { Generalization } from "./components/sections/Generalization";
import { Limitations } from "./components/sections/Limitations";
import { Timeline } from "./components/sections/Timeline";
import { FinalCTA } from "./components/sections/FinalCTA";
import { FutureWork } from "./components/sections/FutureWork";
import { Phase4 } from "./components/sections/Phase4";
import { MotionConfig } from "framer-motion";
import { useEffect } from "react";

function App() {
  // The browser looks for a URL's #section before React has rendered it, so a
  // shared link such as /AeroGuard/#simulator would otherwise open at the top.
  useEffect(() => {
    const id = decodeURIComponent(window.location.hash.slice(1));
    if (id) document.getElementById(id)?.scrollIntoView();
  }, []);

  return (
    // reducedMotion="user": honour the OS "reduce motion" setting for every
    // framer-motion reveal, count-up trigger and looping animation.
    <MotionConfig reducedMotion="user">
      <div className="min-h-screen bg-(--color-void)">
        <Nav />
        <main id="main" tabIndex={-1} className="outline-none">
          <Hero />
          <Scale />
          <Problem />
          <PhysicsEngine />
          <AIPipeline />
          <Intervention />
          <KeyResults />
          <Evaluation />
          <FlightReplay />
          <Simulator />
          <Generalization />
          <Phase4 />
          <Limitations />
          <Timeline />
          <FutureWork />
        </main>
        <FinalCTA />
      </div>
    </MotionConfig>
  );
}

export default App;
