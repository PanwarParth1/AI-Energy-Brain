import { useEffect, useState } from "react";
import { api } from "../services/api";

/** Polls /api/health so the header's connection indicator reflects
 * reality, never a hardcoded "Online". */
export function useApiHealth(intervalMs = 15000) {
  const [status, setStatus] = useState("checking"); // checking | online | offline
  const [lastChecked, setLastChecked] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const data = await api.health();
        if (cancelled) return;
        setStatus(data?.status === "ok" ? "online" : "offline");
      } catch {
        if (!cancelled) setStatus("offline");
      } finally {
        if (!cancelled) setLastChecked(new Date());
      }
    }

    check();
    const id = setInterval(check, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [intervalMs]);

  return { status, lastChecked };
}
