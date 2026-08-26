import "./SectionLabel.css";

interface SectionLabelProps {
  children: string;
}

export function SectionLabel({ children }: SectionLabelProps) {
  return <span className="section-label">{children}</span>;
}
