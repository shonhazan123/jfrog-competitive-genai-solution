import type {
  ComparisonMatrix,
  ComparisonMatrixCell,
  ComparisonStance,
} from "../api/types";

export type Strength = ComparisonStance;

export type ThreatLevel = "High" | "Medium" | "Low";

/** Buyer-facing dimension labels (columns in the transposed grid). */
export const DIMENSION_LABELS: Record<string, string> = {
  artifact_management: "Artifact Management",
  sca_sbom: "SCA / SBOM",
  container_security: "Container Security",
  cicd_integration: "CI/CD Integration",
  developer_experience: "Developer Experience",
};

export const STRENGTH_LABELS: Record<Strength, string> = {
  strong: "Strong",
  moderate: "Moderate",
  weak: "Weak",
  none: "None",
};

export function stanceToStrength(stance: ComparisonStance | undefined): Strength {
  return stance ?? "none";
}

export function dimensionLabel(dimensionKey: string, dimensionName: string): string {
  return DIMENSION_LABELS[dimensionKey] ?? dimensionName;
}

export function getCellForCompetitor(
  matrix: ComparisonMatrix,
  dimensionKey: string,
  competitorSlug: string,
): ComparisonMatrixCell | undefined {
  const dimension = matrix.dimensions.find((row) => row.key === dimensionKey);
  return dimension?.cells.find((cell) => cell.competitor === competitorSlug);
}

export function primaryEvidence(cell: ComparisonMatrixCell | undefined) {
  if (!cell?.evidence.length) return undefined;
  return cell.evidence.find((item) => item.is_primary) ?? cell.evidence[0];
}

const NO_CLAIM_SUMMARY = "No public claim on record.";

/** Deterministic threat from stance counts — omitted when no claims exist. */
export function deriveThreat(
  matrix: ComparisonMatrix,
  competitorSlug: string,
): { level: ThreatLevel; derived: true } | null {
  let strong = 0;
  let moderateWithEvidence = 0;

  for (const dimension of matrix.dimensions) {
    const cell = dimension.cells.find((c) => c.competitor === competitorSlug);
    if (!cell) continue;
    if (cell.stance === "strong") strong += 1;
    if (cell.stance === "moderate" && cell.evidence.length > 0) {
      moderateWithEvidence += 1;
    }
  }

  const claimCount = strong + moderateWithEvidence;
  if (claimCount === 0) return null;

  if (strong >= 2 || moderateWithEvidence >= 3) {
    return { level: "High", derived: true };
  }
  if (strong >= 1 || moderateWithEvidence >= 2) {
    return { level: "Medium", derived: true };
  }
  if (moderateWithEvidence >= 1) {
    return { level: "Low", derived: true };
  }
  return null;
}

export function buildCompetitorSummary(
  matrix: ComparisonMatrix,
  competitorSlug: string,
): string {
  const claims: string[] = [];

  for (const dimension of matrix.dimensions) {
    const cell = dimension.cells.find((c) => c.competitor === competitorSlug);
    if (
      cell &&
      cell.stance !== "none" &&
      cell.summary !== NO_CLAIM_SUMMARY
    ) {
      claims.push(cell.summary);
    }
  }

  if (claims.length === 0) {
    return "No public positioning claims on record across tracked capabilities.";
  }

  return claims.join(" ");
}
