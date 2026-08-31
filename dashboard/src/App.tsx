import { Nav } from "./components/Nav";
import { Hero } from "./components/sections/Hero";
import { Problem } from "./components/sections/Problem";
import { PhysicsEngine } from "./components/sections/PhysicsEngine";
import { AIPipeline } from "./components/sections/AIPipeline";
import { Intervention } from "./components/sections/Intervention";
import { Scale } from "./components/sections/Scale";
import { KeyResults } from "./components/sections/KeyResults";
import { FlightReplay } from "./components/sections/FlightReplay";
import { Simulator } from "./components/sections/Simulator";
import { Generalization } from "./components/sections/Generalization";
import { Limitations } from "./components/sections/Limitations";
import { Timeline } from "./components/sections/Timeline";
import { FinalCTA } from "./components/sections/FinalCTA";

function App() {
  return (
    <div className="min-h-screen bg-(--color-void)">
      <Nav />
      <main>
        <Hero />
        <Scale />
        <Problem />
        <PhysicsEngine />
        <AIPipeline />
        <Intervention />
        <KeyResults />
        <FlightReplay />
        <Simulator />
        <Generalization />
        <Limitations />
        <Timeline />
      </main>
      <FinalCTA />
    </div>
  );
}

export default App;
