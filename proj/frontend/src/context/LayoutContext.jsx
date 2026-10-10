import { createContext, useContext, useState } from "react";

/** Minimal shared UI state (just the mobile sidebar open/close flag) -
 * not a data store, so plain Context is enough; Redux would be
 * over-engineering for one boolean. */
const LayoutContext = createContext(null);

export function LayoutProvider({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  return (
    <LayoutContext.Provider value={{ sidebarOpen, setSidebarOpen }}>
      {children}
    </LayoutContext.Provider>
  );
}

export function useLayout() {
  const ctx = useContext(LayoutContext);
  if (!ctx) throw new Error("useLayout must be used within LayoutProvider");
  return ctx;
}
