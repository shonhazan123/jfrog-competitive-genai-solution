export type NavGroup = "daily" | "reference" | "tools";

export interface NavItem {
  path: string; label: string; group: NavGroup; icon: string; primary?: boolean;
}

/** The information architecture lives here. Regrouping never touches JSX. */
export const NAVIGATION: NavItem[] = [
  { path: "/",            label: "Today",           group: "daily",     icon: "list",    primary: true },
  { path: "/divisions",   label: "Divisions",       group: "daily",     icon: "users",   primary: true },
  { path: "/industry",    label: "Industry",        group: "daily",     icon: "globe",   primary: true },
  { path: "/trajectory",  label: "Trajectory",      group: "reference", icon: "history", primary: false },
  { path: "/comparison",  label: "Comparison",      group: "reference", icon: "chart",   primary: true },
  { path: "/about-us",    label: "Competitors → Us",group: "reference", icon: "eye",     primary: true },
  { path: "/ask",         label: "Ask",             group: "tools",     icon: "message" },
  { path: "/settings",    label: "Settings",        group: "tools",     icon: "gear" },
  { path: "/digest",      label: "Email Digest",    group: "tools",     icon: "mail" },
];

export const GROUP_LABELS: Record<NavGroup, string> = {
  daily: "Daily", reference: "Reference", tools: "Tools",
};
