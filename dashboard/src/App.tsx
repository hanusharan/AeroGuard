import { Nav } from "./components/Nav";
import { Hero } from "./components/sections/Hero";
import { Problem } from "./components/sections/Problem";
import { PhysicsEngine } from "./components/sections/PhysicsEngine";
import { AIPipeline } from "./components/sections/AIPipeline";
import { Scale } from "./components/sections/Scale";
import { KeyResults } from "./components/sections/KeyResults";
import { FlightReplay } from "./components/sections/FlightReplay";
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
        <KeyResults />
        <FlightReplay />
        <Generalization />
        <Limitations />
        <Timeline />
      </main>
      <FinalCTA />
    </div>
  );
}

export default App;
