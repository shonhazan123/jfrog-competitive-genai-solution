import "./FilterChips.css";

interface FilterChipsProps {
  options: string[];
  selected: string;
  onChange: (value: string) => void;
}

export function FilterChips({ options, selected, onChange }: FilterChipsProps) {
  return (
    <div className="filter-chips" role="group">
      {options.map((option) => {
        const isActive = option === selected;
        return (
          <button
            key={option}
            type="button"
            className={isActive ? "filter-chip filter-chip--active" : "filter-chip"}
            aria-pressed={isActive}
            onClick={() => onChange(option)}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}
