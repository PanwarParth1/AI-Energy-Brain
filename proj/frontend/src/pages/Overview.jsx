import { Link } from "react-router-dom";
import { Zap, TrendingUp, Cpu, Bell, ClipboardList, ArrowRight } from "lucide-react";
import Header from "../components/layout/Header";
import { useLayout } from "../context/LayoutContext";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import LoadingState from "../components/ui/LoadingState";
import ErrorState from "../components/ui/ErrorState";
import EmptyState from "../components/ui/EmptyState";
import EnergyHistoryChart from "../components/charts/EnergyHistoryChart";
import RecommendationList from "../components/recommendations/RecommendationList";
import AlertRow from "../components/alerts/AlertRow";
import IntelligenceFlow from "../components/overview/IntelligenceFlow";
import WhatIfAccessCards from "../components/overview/WhatIfAccessCards";
import { useOverviewData } from "../hooks/useOverviewData";
import { formatNumber } from "../utils/format";

function KpiCard({ icon: Icon, label, value, context, tone }) {
  return (
    <div className="border border-slate-800 bg-slate-900/60 p-5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</span>
        <Icon size={16} className="text-slate-600" />
      </div>
      <p className="mt-2 text-2xl font-bold text-slate-100">{value}</p>
      {context && (
        tone ? <div className="mt-1.5"><Badge label={context} tone={tone} /></div>
             : <p className="mt-1 text-xs text-slate-500">{context}</p>
      )}
    </div>
  );
}

function ViewLink({ to, label }) {
  return (
    <Link to={to} className="flex items-center gap-1 text-xs font-medium text-cyan-400 hover:text-cyan-300">
      {label}
      <ArrowRight size={12} />
    </Link>
  );
}

export default function Overview() {
  const { data, loading, error, refetch } = useOverviewData();
  const { setSidebarOpen } = useLayout();

  return (
    <div className="flex-1 overflow-y-auto">
      <Header
        onMenuClick={() => setSidebarOpen(true)}
        title="Industrial Intelligence Control Center"
        subtitle="Monitor energy behaviour, machine health and abnormal operating conditions from a unified AI platform."
      />

      <div className="space-y-6 p-8">
        {loading && <LoadingState label="Loading overview..." />}
        {error && <ErrorState message="Unable to load the dashboard overview." onRetry={refetch} />}

        {data && !loading && !error && (
          <>
            {/* --- A/B/C/D top status section (section 5) --- */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
              <KpiCard
                icon={Zap}
                label="Current Energy"
                value={formatNumber(data.dashboard.energy.current_power, 0)}
                context={data.dashboard.energy.unit}
              />
              <KpiCard
                icon={TrendingUp}
                label="Energy Forecast"
                value={formatNumber(data.dashboard.energy.forecast_power, 0)}
                context={`Next ${data.dashboard.energy.forecast_horizon}`}
              />
              <KpiCard
                icon={Cpu}
                label="Machine Status"
                value={data.dashboard.machines.latest_status}
                context={`Cycle ${data.dashboard.machines.latest_cycle_index} - anomaly detector`}
                tone={data.dashboard.machines.latest_status}
              />
              <KpiCard
                icon={Bell}
                label="Active Alerts"
                value={data.alerts.count}
                context={data.alerts.count > 0 ? data.alerts.alerts[0].severity : "None"}
                tone={data.alerts.count > 0 ? data.alerts.alerts[0].severity : "NORMAL"}
              />
              <KpiCard
                icon={ClipboardList}
                label="Recommendations"
                value={data.dashboard.top_recommendations.length}
                context={data.dashboard.top_recommendations[0]?.priority ?? "None"}
                tone={data.dashboard.top_recommendations[0]?.priority ?? "NORMAL"}
              />
            </div>

            {/* --- intelligence flow (section 6) --- */}
            <Card title="Industrial Intelligence Flow" subtitle="Data -> energy + machine intelligence -> anomaly/efficiency analysis -> decisions">
              <IntelligenceFlow />
            </Card>

            {/* --- energy summary (section 7) --- */}
            <Card
              title="Energy Consumption"
              subtitle="Trailing 24 hours - UCI Tetouan City Power Consumption"
              action={<ViewLink to="/energy" label="View Energy Intelligence" />}
            >
              <EnergyHistoryChart records={data.history.records} />
            </Card>

            {/* --- machine intelligence (section 8) + alert center (section 9) --- */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card
                title="Machine Intelligence"
                subtitle="Hydraulic Test Rig - most recent cycle"
                action={<ViewLink to="/machines" label="Open Machine Health" />}
              >
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Cycle</span>
                    <span className="text-slate-200">{data.dashboard.machines.latest_cycle_index}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Anomaly status</span>
                    <Badge label={data.dashboard.machines.latest_status} />
                  </div>
                  <div className="flex justify-between pt-2 text-xs text-slate-600">
                    <span>Normal</span>
                    <span>{data.dashboard.machines.status_counts.normal} / {data.dashboard.machines.status_counts.total} cycles</span>
                  </div>
                </div>
                {data.dashboard.machines.latest_status !== "NORMAL" && (
                  <p className="mt-3 border-t border-slate-800 pt-3 text-xs text-amber-400">
                    Attention: most recent cycle is not within the reference range.
                  </p>
                )}
                <div className="mt-4 border-t border-slate-800 pt-3">
                  <ViewLink to="/machine-simulator" label="Run What-If Simulation" />
                </div>
              </Card>

              <Card
                title="Active Alerts"
                subtitle="Current snapshot - not a historical log"
                action={<ViewLink to="/alerts" label="View All Alerts" />}
              >
                {data.alerts.count === 0 ? (
                  <EmptyState message="No active alerts" />
                ) : (
                  <div className="space-y-3">
                    {data.alerts.alerts.slice(0, 4).map((alert) => (
                      <AlertRow key={alert.alert_id} alert={alert} />
                    ))}
                  </div>
                )}
              </Card>
            </div>

            {/* --- recommendation center (section 10) --- */}
            <Card
              title="AI Recommendations"
              subtitle="Top priority, current state"
              action={<ViewLink to="/recommendations" label="View All Recommendations" />}
            >
              <RecommendationList recommendations={data.dashboard.top_recommendations} />
            </Card>

            {/* --- what-if scenario access (section 11) --- */}
            <div>
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">What-If Scenarios</p>
              <WhatIfAccessCards />
            </div>

            <Card title="Data Context" subtitle="Dataset provenance - shown, not hidden">
              <div className="grid grid-cols-1 gap-4 text-xs text-slate-400 sm:grid-cols-2">
                <div>
                  <p className="font-semibold text-slate-300">Energy dataset</p>
                  <p className="mt-1">{data.dashboard.energy.dataset}</p>
                  <p className="mt-1 text-slate-500">
                    Public city-level power consumption, 10-minute intervals. Does not represent live
                    industrial machine energy consumption, and contains no production variable - the
                    Energy + Production What-If uses manual scenario inputs only.
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-slate-300">Machine dataset</p>
                  <p className="mt-1">UCI Condition Monitoring of Hydraulic Systems</p>
                  <p className="mt-1 text-slate-500">
                    Controlled experimental test-rig data, not a live industrial facility.
                  </p>
                </div>
              </div>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
