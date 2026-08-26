import { Outlet } from "react-router-dom";
import { Sidebar } from "../components/nav/Sidebar";
import { BottomBar } from "../components/nav/BottomBar";

export function AppShell() {
  return (
    <div className="app-shell">
      <header className="status-strip" aria-label="Run status">
        <span>Last run · sources · counts · Run now</span>
      </header>
      <div className="app-shell__body">
        <Sidebar />
        <main className="app-shell__main">
          <Outlet />
        </main>
      </div>
      <BottomBar />
    </div>
  );
}
