import "./WasNow.css";

interface WasNowProps {
  was: string;
  now: string;
}

export function WasNow({ was, now }: WasNowProps) {
  return (
    <span className="was-now">
      <span className="was-now__part">
        <span className="was-now__label">was</span>
        <span className="was-now__value">{was}</span>
      </span>
      <span className="was-now__arrow" aria-hidden="true">
        →
      </span>
      <span className="was-now__part">
        <span className="was-now__label">now</span>
        <span className="was-now__value">{now}</span>
      </span>
    </span>
  );
}
