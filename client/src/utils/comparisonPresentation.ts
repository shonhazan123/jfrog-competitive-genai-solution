import type {
  ComparisonMatrix,
  ComparisonMatrixCell,
  ComparisonStance,
} from "../api/types";

export type Strength = "strong" | "moderate" | "weak" | "none";

export type ThreatLevel = "High" | "Medium" | "Low";

/** Figma-aligned labels for JFrog component keys (columns in the transposed grid). */
export const DIMENSION_LABELS: Record<string, string> = {
  artifactory: "Artifact Management",
  xray: "SCA / SBOM",
  curation: "Policy & Curation",
  apptrust: "Build Provenance",
  advanced_security: "Container Security",
  ai_ml: "AI / ML",
};

export const STRENGTH_LABELS: Record<Strength, string> = {
  strong: "Strong",
  moderate: "Moderate",
  weak: "Weak",
  none: "None",
};

export function stanceToStrength(stance: ComparisonStance): Strength {
  switch (stance) {
    case "ahead":
      return "strong";
    case "comparable":
      return "moderate";
    case "behind":
      return "weak";
    case "no_claim":
      return "none";
  }
}

export function dimensionLabel(componentKey: string, componentName: string): string {
  return DIMENSION_LABELS[componentKey] ?? componentName;
}

export function getCellForCompetitor(
  matrix: ComparisonMatrix,
  componentKey: string,
  competitorSlug: string,
): ComparisonMatrixCell | undefined {
  const component = matrix.components.find((row) => row.key === componentKey);
  return component?.cells.find((cell) => cell.competitor === competitorSlug);
}

export function primaryEvidence(cell: ComparisonMatrixCell | undefined) {
  if (!cell?.evidence.length) return undefined;
  return cell.evidence.find((item) => item.is_primary) ?? cell.evidence[0];
}

/** Deterministic threat from stance counts — omitted when no claims exist. */
export function deriveThreat(
  matrix: ComparisonMatrix,
  competitorSlug: string,
): { level: ThreatLevel; derived: true } | null {
  let ahead = 0;
  let comparableWithEvidence = 0;

  for (const component of matrix.components) {
    const cell = component.cells.find((c) => c.competitor === competitorSlug);
    if (!cell) continue;
    if (cell.stance === "ahead") ahead += 1;
    if (cell.stance === "comparable" && cell.evidence.length > 0) {
      comparableWithEvidence += 1;
    }
  }

  const claimCount = ahead + comparableWithEvidence;
  if (claimCount === 0) return null;

  if (ahead >= 2 || comparableWithEvidence >= 3) {
    return { level: "High", derived: true };
  }
  if (ahead >= 1 || comparableWithEvidence >= 2) {
    return { level: "Medium", derived: true };
  }
  if (comparableWithEvidence >= 1) {
    return { level: "Low", derived: true };
  }
  return null;
}

export function buildCompetitorSummary(
  matrix: ComparisonMatrix,
  competitorSlug: string,
): string {
  const claims: string[] = [];

  for (const component of matrix.components) {
    const cell = component.cells.find((c) => c.competitor === competitorSlug);
    if (
      cell &&
      cell.stance !== "no_claim" &&
      cell.summary !== "No public claim on record."
    ) {
      claims.push(cell.summary);
    }
  }

  if (claims.length === 0) {
    return "No public positioning claims on record across tracked capabilities.";
  }

  return claims.join(" ");
}
