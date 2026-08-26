import "./GradeChip.css";

const RELIABILITY_PHRASES: Record<string, string> = {
  A: "completely reliable",
  B: "usually reliable",
  C: "fairly reliable",
  D: "not usually reliable",
  E: "unreliable",
  F: "reliability cannot be judged",
};

function getReliabilityPhrase(grade: string): string {
  const letter = grade.charAt(0).toUpperCase();
  return RELIABILITY_PHRASES[letter] ?? "reliability cannot be judged";
}

function getExtremeClass(grade: string): string | undefined {
  const letter = grade.charAt(0).toUpperCase();
  if (letter === "A") return "grade-chip--strong";
  if (letter === "E" || letter === "F") return "grade-chip--weak";
  return undefined;
}

interface GradeChipProps {
  grade: string;
}

export function GradeChip({ grade }: GradeChipProps) {
  const phrase = getReliabilityPhrase(grade);
  const extremeClass = getExtremeClass(grade);
  const title = `Grade ${grade}: ${phrase}`;

  return (
    <span
      className={["grade-chip", extremeClass].filter(Boolean).join(" ")}
      title={title}
    >
      {grade}
    </span>
  );
}
