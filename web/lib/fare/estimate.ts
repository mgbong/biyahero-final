/**
 * Segment fare from configurable fare_rules only.
 * Discounts are applied only when an active DiscountRule is passed in (Phase 5).
 */

import type { DiscountRule, FareRule, TransportType } from "@/lib/types/database";

export function pickFareRule(
  rules: FareRule[],
  transportType: TransportType
): FareRule | null {
  const active = rules.filter(
    (r) =>
      r.active &&
      r.transport_type === transportType &&
      transportType !== "walk_link"
  );
  return active[0] ?? null;
}

/** base + per_km * km, floored at min_fare when set. */
export function estimateSegmentFare(
  rule: FareRule | null,
  distanceM: number
): number {
  if (!rule) return 0;
  const km = Math.max(0, distanceM) / 1000;
  let fare = rule.base_fare + rule.per_km_rate * km;
  if (rule.min_fare != null) fare = Math.max(fare, rule.min_fare);
  return Math.round(fare * 100) / 100;
}

/**
 * Apply discount ONLY from an active DB rule. Never hardcode percents here.
 * If no active rule is supplied, returns the base fare unchanged.
 */
export function applyDiscount(
  fare: number,
  rule: DiscountRule | null | undefined
): { fare: number; discountApplied: boolean; discountType: string | null } {
  if (!rule || !rule.active) {
    return { fare, discountApplied: false, discountType: null };
  }
  const cut = fare * (rule.percent / 100);
  const next = Math.round((fare - cut) * 100) / 100;
  return {
    fare: Math.max(0, next),
    discountApplied: true,
    discountType: rule.type,
  };
}
