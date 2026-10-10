import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/layout/Sidebar";
import Overview from "./pages/Overview";
import EnergyIntelligence from "./pages/EnergyIntelligence";
import MachineHealth from "./pages/MachineHealth";
import MachineSimulator from "./pages/MachineSimulator";
import Alerts from "./pages/Alerts";
import Recommendations from "./pages/Recommendations";
import { LayoutProvider, useLayout } from "./context/LayoutContext";

function Shell() {
  const { sidebarOpen, setSidebarOpen } = useLayout();
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/energy" element={<EnergyIntelligence />} />
        <Route path="/machines" element={<MachineHealth />} />
        <Route path="/machine-simulator" element={<MachineSimulator />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/recommendations" element={<Recommendations />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <LayoutProvider>
      <Shell />
    </LayoutProvider>
  );
}
