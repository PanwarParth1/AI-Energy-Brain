import Header from "../components/layout/Header";
import { useLayout } from "../context/LayoutContext";
import Card from "../components/ui/Card";
import LoadingState from "../components/ui/LoadingState";
import ErrorState from "../components/ui/ErrorState";
import EmptyState from "../components/ui/EmptyState";
import AlertRow from "../components/alerts/AlertRow";
import { useFetch } from "../hooks/useFetch";
import { api } from "../services/api";

export default function Alerts() {
  const { data, loading, error, refetch } = useFetch(() => api.getAlerts(), []);
  const { setSidebarOpen } = useLayout();

  return (
    <div className="flex-1 overflow-y-auto">
      <Header onMenuClick={() => setSidebarOpen(true)} title="Alerts" subtitle="Current status derived from machine anomaly detection and AI recommendations." />

      <div className="space-y-6 p-8">
        <div className="border border-slate-800 bg-slate-900/40 px-4 py-3 text-xs text-slate-500">
          This view represents the current snapshot from the backend. The system does not yet provide a
          historical alert log - alerts here reflect the most recently evaluated cycle only.
        </div>

        <Card title={`Alerts (${data?.count ?? "..."})`}>
          {loading && <LoadingState label="Loading alerts..." />}
          {error && <ErrorState message="Unable to load alerts." onRetry={refetch} />}
          {data && !loading && data.alerts.length === 0 && <EmptyState message="No active alerts" />}
          {data && !loading && data.alerts.length > 0 && (
            <div className="space-y-3">
              {data.alerts.map((alert) => (
                <AlertRow key={alert.alert_id} alert={alert} />
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
