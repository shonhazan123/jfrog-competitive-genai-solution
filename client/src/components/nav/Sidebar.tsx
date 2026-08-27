import { NavLink } from "react-router-dom";
import clsx from "clsx";
import type { RunStatus } from "../../api/types";
import { NAVIGATION, GROUP_LABELS, type NavGroup } from "../../config/navigation";
import { NavIcon } from "./NavIcon";
import { SidebarMeta } from "./SidebarMeta";

const GROUP_ORDER: NavGroup[] = ["daily", "reference", "tools"];

interface SidebarProps {
  runStatus?: RunStatus;
}

export function Sidebar({ runStatus }: SidebarProps) {
  return (
    <aside className="sidebar" data-testid="sidebar" aria-label="Main navigation">
      <div className="sidebar__logo">
        <div className="sidebar__logo-mark" aria-hidden="true">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 7 L7 2 L12 7 L7 12 Z" fill="white" />
            <circle cx="7" cy="7" r="2" fill="var(--brand-jfrog)" />
          </svg>
        </div>
        <div className="sidebar__logo-text">
          <div className="mono-label sidebar__logo-brand">JFrog</div>
          <div className="sidebar__logo-title">Intel</div>
        </div>
      </div>

      <nav className="sidebar__nav">
        {GROUP_ORDER.map((group) => {
          const items = NAVIGATION.filter((item) => item.group === group);
          if (items.length === 0) return null;

          return (
            <div key={group} className="sidebar__group">
              {group !== "daily" ? (
                <div className="sidebar__group-label mono-label">{GROUP_LABELS[group]}</div>
              ) : null}
              {items.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === "/"}
                  className={({ isActive }) =>
                    clsx("sidebar__link", isActive && "sidebar__link--active")
                  }
                >
                  <NavIcon name={item.icon} />
                  <span className="sidebar__link-label">{item.label}</span>
                  {item.path === "/" ? (
                    <span
                      className="sidebar__today-dot"
                      data-testid="sidebar-today-dot"
                      aria-hidden="true"
                    />
                  ) : null}
                </NavLink>
              ))}
            </div>
          );
        })}
      </nav>

      <div className="sidebar__footer">
        <SidebarMeta data={runStatus} />
      </div>
    </aside>
  );
}
