import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
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

  return (
    <div className="app-shell">
      <header className="status-strip" aria-label="Run status">
        <span>Last run · sources · counts · Run now</span>
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
