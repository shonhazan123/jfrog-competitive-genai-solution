interface NavIconProps {
  name: string;
  className?: string;
}

export function NavIcon({ name, className }: NavIconProps) {
  const cls = className ?? "sidebar__link-icon";

  switch (name) {
    case "list":
      return (
        <svg className={cls} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <rect x="2" y="2" width="5" height="5" rx="1" fill="currentColor" opacity="0.9" />
          <rect x="9" y="2" width="5" height="5" rx="1" fill="currentColor" opacity="0.4" />
          <rect x="2" y="9" width="5" height="5" rx="1" fill="currentColor" opacity="0.4" />
          <rect x="9" y="9" width="5" height="5" rx="1" fill="currentColor" opacity="0.4" />
        </svg>
      );
    case "chart":
      return (
        <svg className={cls} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" />
          <line x1="2" y1="8" x2="14" y2="8" stroke="currentColor" strokeWidth="1.5" />
          <path d="M8 2 C10.5 4 10.5 12 8 14" stroke="currentColor" strokeWidth="1.5" fill="none" />
          <path d="M8 2 C5.5 4 5.5 12 8 14" stroke="currentColor" strokeWidth="1.5" fill="none" />
        </svg>
      );
    case "activity":
      return (
        <svg className={cls} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path
            d="M2 12 L6 7 L9 10 L13 4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="13" cy="4" r="1.5" fill="currentColor" />
        </svg>
      );
    case "globe":
      return (
        <svg className={cls} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <rect x="1" y="10" width="3" height="5" rx="0.5" fill="currentColor" opacity="0.5" />
          <rect x="6" y="6" width="3" height="9" rx="0.5" fill="currentColor" opacity="0.7" />
          <rect x="11" y="2" width="3" height="13" rx="0.5" fill="currentColor" />
        </svg>
      );
    case "message":
      return (
        <svg className={cls} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path
            d="M2 2h12a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H5l-3 3V3a1 1 0 0 1 1-1z"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
            strokeLinejoin="round"
          />
          <circle cx="5.5" cy="6.5" r="0.75" fill="currentColor" />
          <circle cx="8" cy="6.5" r="0.75" fill="currentColor" />
          <circle cx="10.5" cy="6.5" r="0.75" fill="currentColor" />
        </svg>
      );
    case "users":
      return (
        <svg className={cls} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="6" cy="5" r="2.5" stroke="currentColor" strokeWidth="1.5" />
          <path
            d="M1 14c0-2.5 2.2-4 5-4s5 1.5 5 4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <circle cx="11.5" cy="5.5" r="2" stroke="currentColor" strokeWidth="1.5" />
          <path d="M14 14c0-2-1.5-3.5-3.5-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "gear":
      return (
        <svg className={cls} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.5" />
          <path
            d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.05 3.05l1.06 1.06M11.94 11.94l1.06 1.06M3.05 12.95l1.06-1.06M11.94 4.06l1.06-1.06"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      );
    case "mail":
      return (
        <svg className={cls} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <rect x="1.5" y="3.5" width="13" height="9" rx="1" stroke="currentColor" strokeWidth="1.5" />
          <path d="M1.5 4.5 L8 9 L14.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    default:
      return null;
  }
}
