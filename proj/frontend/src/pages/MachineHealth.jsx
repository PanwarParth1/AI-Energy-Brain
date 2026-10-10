import Header from "../components/layout/Header";
import { useLayout } from "../context/LayoutContext";
import Card from "../components/ui/Card";
import LoadingState from "../components/ui/LoadingState";
import ErrorState from "../components/ui/ErrorState";
import Badge from "../components/ui/Badge";
import MachineHealthCard from "../components/machine/MachineHealthCard";
import AnomalyCard from "../components/machine/AnomalyCard";
import CycleAnalyzer from "../components/machine/CycleAnalyzer";
import { useFetch } from "../hooks/useFetch";
import { api } from "../services/api";

export default function MachineHealth() {
  const { setSidebarOpen } = useLayout();
  const { data: machines, loading: machinesLoading, error: machinesError, refetch: refetchMachines } =
    useFetch(() => api.getMachines(), []);

  const machine = machines?.machines?.[0];
  const maxCycleIndex = machine ? machine.n_cycles_available - 1 : undefined;

  const { data: health, loading: healthLoading, error: healthError } = useFetch(
    () => (machine ? api.getMachineHealth(machine.machine_id) : Promise.resolve(null)),
    [machine?.machine_id]
  );
  const { data: anomaly, loading: anomalyLoading, error: anomalyError } = useFetch(
    () => (machine ? api.getMachineAnomaly(machine.machine_id) : Promise.resolve(null)),
    [machine?.machine_id]
  );

  return (
    <div className="flex-1 overflow-y-auto">
      <Header onMenuClick={() => setSidebarOpen(true)} title="Machine Health" subtitle="Condition classification, anomaly detection and diagnostic analysis." />

      <div className="space-y-6 p-8">
        {machinesLoading && <LoadingState label="Loading machine list..." />}
        {machinesError && <ErrorState message="Unable to load machine list." onRetry={refetchMachines} />}

        {machine && (
          <Card title={machine.name} subtitle={`${machine.source} - ${machine.dataset_type}`}>
            <p className="text-xs text-slate-500">
              {machine.n_cycles_available.toLocaleString()} cycles available. This dashboard represents one
              dataset/test rig - it does not fabricate a machine fleet.
            </p>
          </Card>
        )}

        {machine && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card title="Health Classification" subtitle="Most recent available cycle">
              {healthLoading && <LoadingState label="Loading machine health..." />}
              {healthError && <ErrorState message="Unable to load machine health." />}
              {health && !healthLoading && <MachineHealthCard health={health} />}
            </Card>
            <Card title="Anomaly Detection" subtitle="Most recent available cycle">
              {anomalyLoading && <LoadingState label="Loading anomaly detection..." />}
              {anomalyError && <ErrorState message="Unable to load anomaly detection." />}
              {anomaly && !anomalyLoading && <AnomalyCard anomaly={anomaly} />}
            </Card>
          </div>
        )}

        {machine && (
          <Card title="Cycle Analysis" subtitle="Run Parts 7, 8 and 9 together for any real cycle in the dataset">
            <CycleAnalyzer maxCycleIndex={maxCycleIndex} />
          </Card>
        )}
      </div>
    </div>
  );
}
