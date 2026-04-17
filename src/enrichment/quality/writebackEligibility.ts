import type { TargetRole } from "../types/prospect";
import type { ResolvedRoleDecision } from "../types/resolution";
import type { ResolvedEmailDecision } from "../types/email";
import type {
  WritebackEligibilityStatus,
  WritebackEligibilityDecision,
  WritebackFieldDecision,
  PersonPlausibilityDecision,
} from "../types/quality";
import { evaluatePersonPlausibility } from "./personPlausibility";

// ---------------------------------------------------------------------------
// Field-level writeback policies
// ---------------------------------------------------------------------------

function evaluateRoleNameWriteback(
  roleDecision: ResolvedRoleDecision,
  plausibility: PersonPlausibilityDecision,
): WritebackFieldDecision {
  const field = `${roleDecision.role}_NAME`;

  if (!roleDecision.chosenCandidate) {
    return { field, status: "BLOCKED", value: null, reason: "No resolved candidate" };
  }

  if (plausibility.status === "IMPLAUSIBLE") {
    return {
      field,
      status: "BLOCKED",
      value: null,
      reason: `Person "${plausibility.personName}" failed plausibility check (score: ${plausibility.score})`,
    };
  }

  if (plausibility.status === "SUSPICIOUS") {
    return {
      field,
      status: "REVIEW",
      value: roleDecision.chosenCandidate.fullName,
      reason: `Person "${plausibility.personName}" is suspicious (score: ${plausibility.score}): ${plausibility.negativeSignals.join(", ")}`,
    };
  }

  const roleStatus = roleDecision.status;
  if (roleStatus === "RESOLVED_STRONG") {
    return {
      field,
      status: "ELIGIBLE",
      value: roleDecision.chosenCandidate.fullName,
      reason: "Person is plausible and role resolution is STRONG",
    };
  }

  if (roleStatus === "RESOLVED_PROBABLE") {
    return {
      field,
      status: "ELIGIBLE",
      value: roleDecision.chosenCandidate.fullName,
      reason: "Person is plausible and role resolution is PROBABLE",
    };
  }

  // UNRESOLVED_WEAK or UNRESOLVED_NONE
  return {
    field,
    status: "REVIEW",
    value: roleDecision.chosenCandidate.fullName,
    reason: `Role resolution is ${roleStatus} — needs manual review`,
  };
}

function evaluateLinkedinWriteback(
  roleDecision: ResolvedRoleDecision,
  plausibility: PersonPlausibilityDecision,
): WritebackFieldDecision {
  const field = `${roleDecision.role}_LINKEDIN`;

  if (!roleDecision.chosenCandidate?.linkedinUrl) {
    return { field, status: "BLOCKED", value: null, reason: "No LinkedIn URL" };
  }

  if (plausibility.status === "IMPLAUSIBLE") {
    return {
      field,
      status: "BLOCKED",
      value: null,
      reason: "Person failed plausibility — LinkedIn URL not trustworthy",
    };
  }

  const url = roleDecision.chosenCandidate.linkedinUrl;

  // Must be a person profile, not a company page
  if (!url.includes("/in/")) {
    return {
      field,
      status: "BLOCKED",
      value: null,
      reason: `URL "${url}" is not a person profile (/in/) link`,
    };
  }

  if (plausibility.status === "SUSPICIOUS") {
    return {
      field,
      status: "REVIEW",
      value: url,
      reason: "Person is suspicious — LinkedIn URL needs review",
    };
  }

  const roleStatus = roleDecision.status;
  if (roleStatus === "RESOLVED_STRONG" || roleStatus === "RESOLVED_PROBABLE") {
    return {
      field,
      status: "ELIGIBLE",
      value: url,
      reason: `LinkedIn URL validated for plausible person with ${roleStatus} role`,
    };
  }

  return {
    field,
    status: "REVIEW",
    value: url,
    reason: `Role resolution is ${roleStatus} — LinkedIn URL needs review`,
  };
}

function evaluateEmailWriteback(
  emailDecision: ResolvedEmailDecision | null,
  plausibility: PersonPlausibilityDecision,
): WritebackFieldDecision {
  const field = `${plausibility.role}_EMAIL`;

  if (!emailDecision || !emailDecision.chosenEmail) {
    return { field, status: "BLOCKED", value: null, reason: "No resolved email" };
  }

  if (plausibility.status === "IMPLAUSIBLE") {
    return {
      field,
      status: "BLOCKED",
      value: null,
      reason: "Person failed plausibility — email not trustworthy",
    };
  }

  const emailStatus = emailDecision.status;
  const emailConf = emailDecision.confidenceLabel;

  // Public email with plausible person — eligible
  if (emailStatus === "RESOLVED_PUBLIC") {
    if (plausibility.status === "SUSPICIOUS") {
      return {
        field,
        status: "REVIEW",
        value: emailDecision.chosenEmail,
        reason: "Public email found but person is suspicious",
      };
    }
    return {
      field,
      status: "ELIGIBLE",
      value: emailDecision.chosenEmail,
      reason: "Public email matched to plausible person",
    };
  }

  // Inferred email — stricter checks
  if (emailStatus === "RESOLVED_INFERRED") {
    if (plausibility.status === "SUSPICIOUS") {
      return {
        field,
        status: "BLOCKED",
        value: null,
        reason: "Inferred email for suspicious person — too risky",
      };
    }

    if (emailConf === "STRONG") {
      return {
        field,
        status: "ELIGIBLE",
        value: emailDecision.chosenEmail,
        reason: "Inferred email with STRONG confidence for plausible person",
      };
    }

    if (emailConf === "PROBABLE") {
      return {
        field,
        status: "REVIEW",
        value: emailDecision.chosenEmail,
        reason: "Inferred email with PROBABLE confidence — needs verification",
      };
    }

    // WEAK
    return {
      field,
      status: "BLOCKED",
      value: null,
      reason: "Inferred email with WEAK confidence — not reliable enough",
    };
  }

  return { field, status: "BLOCKED", value: null, reason: "Email is unresolved" };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function getWritebackEligibility(
  roleDecision: ResolvedRoleDecision,
  emailDecision: ResolvedEmailDecision | null,
): WritebackEligibilityDecision {
  const personName = roleDecision.chosenCandidate?.fullName ?? "";
  const linkedinUrl = roleDecision.chosenCandidate?.linkedinUrl ?? "";
  const roleConfLabel = roleDecision.chosenCandidate?.confidenceLabel ?? null;

  const plausibility = evaluatePersonPlausibility(
    personName,
    roleDecision.companyName,
    roleDecision.role,
    linkedinUrl,
    roleConfLabel,
  );

  const nameField = evaluateRoleNameWriteback(roleDecision, plausibility);
  const linkedinField = evaluateLinkedinWriteback(roleDecision, plausibility);
  const emailField = evaluateEmailWriteback(emailDecision, plausibility);

  const fields = [nameField, linkedinField, emailField];
  const notes: string[] = [];

  // Overall status: worst of all fields that have a value
  let overallStatus: WritebackEligibilityStatus = "ELIGIBLE";
  const activeFields = fields.filter((f) => f.value !== null);

  if (activeFields.length === 0) {
    overallStatus = "BLOCKED";
    notes.push("No writable fields");
  } else {
    if (activeFields.some((f) => f.status === "BLOCKED")) {
      // If some fields are blocked but others are eligible, overall is REVIEW
      const nonBlocked = activeFields.filter((f) => f.status !== "BLOCKED");
      if (nonBlocked.length > 0) {
        overallStatus = "REVIEW";
        notes.push("Some fields blocked, others may be writable");
      } else {
        overallStatus = "BLOCKED";
      }
    } else if (activeFields.some((f) => f.status === "REVIEW")) {
      overallStatus = "REVIEW";
    }
  }

  return {
    sourceFile: roleDecision.sourceFile,
    sheetName: roleDecision.sheetName,
    rowIndex: roleDecision.rowIndex,
    companyName: roleDecision.companyName,
    role: roleDecision.role,
    overallStatus,
    plausibility,
    fields,
    notes,
  };
}
