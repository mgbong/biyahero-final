import type { VerificationStatus } from "@/lib/types/database";

export function verificationLabel(status: VerificationStatus): string {
  switch (status) {
    case "verified":
      return "Verified";
    case "pending_verification":
      return "Pending verification";
    case "potentially_outdated":
      return "Potentially outdated";
    default:
      return "Unknown";
  }
}

/** Never treat non-verified as verified in UI copy. */
export function isVerified(status: VerificationStatus): boolean {
  return status === "verified";
}

export function verificationBadgeClass(status: VerificationStatus): string {
  switch (status) {
    case "verified":
      return "bg-emerald-100 text-emerald-800";
    case "pending_verification":
      return "bg-amber-100 text-amber-900";
    case "potentially_outdated":
      return "bg-rose-100 text-rose-800";
    default:
      return "bg-neutral-100 text-neutral-700";
  }
}
