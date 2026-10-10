/**
 * Single place where the frontend talks to the backend.
 * Components never call fetch() directly - they import from here.
 *
 * Every function returns the JSON body already parsed, or throws an
 * ApiError with { code, message } taken from the backend's own
 * consistent error envelope ({"error": {"code","message"}}) - see
 * backend/app/core/errors.py.
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(code, message, status) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request(path, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });
  } catch (err) {
    clearTimeout(timer);
    if (err.name === "AbortError") {
      throw new ApiError("TIMEOUT", "The request took too long to respond.", 0);
    }
    throw new ApiError("NETWORK_ERROR", "Could not reach the backend API.", 0);
  }
  clearTimeout(timer);

  let body = null;
  try {
    body = await response.json();
  } catch {
    // no JSON body
  }

  if (!response.ok) {
    const err = body?.error ?? {};
    throw new ApiError(
      err.code ?? "UNKNOWN_ERROR",
      err.message ?? `Request failed with status ${response.status}.`,
      response.status
    );
  }

  return body;
}

export const api = {
  // --- system ---
  health: () => request("/api/health"),

  // --- energy ---
  getEnergySummary: () => request("/api/energy/summary"),
  getEnergyHistory: ({ limit, start, end } = {}) => {
    const params = new URLSearchParams();
    if (limit) params.set("limit", limit);
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    const qs = params.toString();
    return request(`/api/energy/history${qs ? `?${qs}` : ""}`);
  },
  getEnergyForecast: (horizon = 6) => request(`/api/energy/forecast?horizon=${horizon}`),
  simulateEnergyProduction: (baselineProduction, baselineEnergy, scenarioProduction, scenarioEnergy) =>
    request("/api/energy/simulate", {
      method: "POST",
      body: JSON.stringify({
        baseline_production: baselineProduction,
        baseline_energy: baselineEnergy,
        scenario_production: scenarioProduction,
        scenario_energy: scenarioEnergy,
      }),
    }),

  // --- machines ---
  getMachines: () => request("/api/machines"),
  getMachineHealth: (machineId, cycleIndex) =>
    request(
      `/api/machines/${machineId}/health${cycleIndex != null ? `?cycle_index=${cycleIndex}` : ""}`
    ),
  getMachineAnomaly: (machineId, cycleIndex) =>
    request(
      `/api/machines/${machineId}/anomaly${cycleIndex != null ? `?cycle_index=${cycleIndex}` : ""}`
    ),
  analyzeMachine: (cycleIndex) =>
    request("/api/machines/analyze", {
      method: "POST",
      body: JSON.stringify({ cycle_index: cycleIndex }),
    }),

  // --- what-if simulation (Part 12/13) ---
  getSimulatableSensors: () => request("/api/machines/simulate/sensors"),
  simulateMachine: (machineId, baselineCycleIndex, perturbations) =>
    request("/api/machines/simulate", {
      method: "POST",
      body: JSON.stringify({
        machine_id: machineId,
        baseline_cycle_index: baselineCycleIndex,
        perturbations,
      }),
    }),

  // --- recommendations ---
  getRecommendations: () => request("/api/recommendations"),
  generateRecommendations: (cycleIndex, includeEnergy = false) =>
    request("/api/recommendations/generate", {
      method: "POST",
      body: JSON.stringify({ cycle_index: cycleIndex, include_energy: includeEnergy }),
    }),

  // --- alerts ---
  getAlerts: () => request("/api/alerts"),

  // --- dashboard ---
  getDashboardSummary: () => request("/api/dashboard/summary"),
};
