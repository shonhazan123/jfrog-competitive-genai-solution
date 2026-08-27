export type NavGroup = "daily" | "reference" | "tools";

export interface NavItem {
  path: string; label: string; group: NavGroup; icon: string; primary?: boolean;
}

/** The information architecture lives here. Regrouping never touches JSX. */
export const NAVIGATION: NavItem[] = [
  { path: "/",           label: "Today",        group: "daily",     icon: "list",     primary: true },
  { path: "/comparison", label: "Competitors",  group: "daily",     icon: "chart",    primary: true },
  { path: "/signals",    label: "Signals",      group: "daily",     icon: "activity", primary: true },
  { path: "/industry",   label: "Industry",     group: "daily",     icon: "globe",    primary: true },
  { path: "/divisions",  label: "Divisions",    group: "reference", icon: "users",    primary: true },
  { path: "/ask",        label: "Ask",          group: "tools",     icon: "message" },
  { path: "/settings",   label: "Settings",     group: "tools",     icon: "gear" },
  { path: "/digest",     label: "Email Digest", group: "tools",     icon: "mail" },
];

export const GROUP_LABELS: Record<NavGroup, string> = {
  daily: "Daily", reference: "Reference", tools: "Tools",
};
