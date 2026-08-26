import { NavLink } from "react-router-dom";
import clsx from "clsx";
import { NAVIGATION, GROUP_LABELS, type NavGroup } from "../../config/navigation";

const GROUP_ORDER: NavGroup[] = ["daily", "reference", "tools"];

export function Sidebar() {
  return (
    <nav className="sidebar" data-testid="sidebar" aria-label="Main navigation">
      {GROUP_ORDER.map((group) => {
        const items = NAVIGATION.filter((item) => item.group === group);
        if (items.length === 0) return null;

        return (
          <div key={group} className="sidebar__group">
            <div className="sidebar__group-label">{GROUP_LABELS[group]}</div>
            {items.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                className={({ isActive }) =>
                  clsx("sidebar__link", isActive && "sidebar__link--active")
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        );
      })}
    </nav>
  );
}
