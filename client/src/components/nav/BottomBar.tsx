import { NavLink } from "react-router-dom";
import clsx from "clsx";
import { NAVIGATION } from "../../config/navigation";

export function BottomBar() {
  const primaryItems = NAVIGATION.filter((item) => item.primary);

  return (
    <nav className="bottom-bar" aria-label="Primary navigation">
      {primaryItems.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          end={item.path === "/"}
          data-testid="bottom-nav-item"
          className={({ isActive }) =>
            clsx("bottom-bar__item", isActive && "bottom-bar__item--active")
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
