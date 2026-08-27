import { NavLink } from "react-router-dom";
import clsx from "clsx";
import { NAVIGATION } from "../../config/navigation";
import { NavIcon } from "./NavIcon";

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
          <NavIcon name={item.icon} className="bottom-bar__icon" />
          <span className="bottom-bar__label">{item.label}</span>
          {item.path === "/" ? (
            <span className="bottom-bar__today-dot" aria-hidden="true" />
          ) : null}
        </NavLink>
      ))}
    </nav>
  );
}
