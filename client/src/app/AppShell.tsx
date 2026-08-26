import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Outlet } from "react-router-dom";
import { api } from "../api/client";
import type { RunStatus } from "../api/types";
import runStatusFixture from "../fixtures/run_status.json";
import { StatusStrip } from "../components/StatusStrip";
import { Sidebar } from "../components/nav/Sidebar";
import { BottomBar } from "../components/nav/BottomBar";

const MOBILE_BREAKPOINT = 900;

function useViewportWidth(): number {
  const [width, setWidth] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth : 1024,
  );

  useEffect(() => {
    const handleResize = () => setWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return width;
}

export function AppShell() {
  const isMobile = useViewportWidth() < MOBILE_BREAKPOINT;
  const { data: runStatus } = useQuery({
    queryKey: ["run-status"],
    queryFn: () => api.getRunStatus(),
    initialData: runStatusFixture as RunStatus,
  });

  return (
    <div className="app-shell">
      <header className="status-strip" aria-label="Run status">
        <StatusStrip data={runStatus} />
      </header>
      <div className="app-shell__body">
        {!isMobile ? <Sidebar /> : null}
        <main className="app-shell__main">
          <Outlet />
        </main>
      </div>
      {isMobile ? <BottomBar /> : null}
    </div>
  );
}
