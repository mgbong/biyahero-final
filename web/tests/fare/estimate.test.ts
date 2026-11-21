import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  applyDiscount,
  estimateSegmentFare,
  pickFareRule,
} from "../../lib/fare/estimate";
import { SEED_FARE_RULES } from "../../lib/geo/naga-seed";
import type { DiscountRule } from "../../lib/types/database";

describe("fare estimate", () => {
  it("uses base + per-km from fare rules", () => {
    const rule = pickFareRule(SEED_FARE_RULES, "jeepney");
    assert.ok(rule);
    const fare = estimateSegmentFare(rule, 2000); // 2 km
    // 13 + 1.8*2 = 16.6
    assert.equal(fare, 16.6);
  });

  it("respects min_fare", () => {
    const rule = pickFareRule(SEED_FARE_RULES, "jeepney");
    const fare = estimateSegmentFare(rule, 100); // short hop
    assert.equal(fare, 13);
  });

  it("does not apply inactive discount rules", () => {
    const inactive: DiscountRule = {
      id: "x",
      type: "student",
      percent: 20,
      requires_validation: true,
      active: false,
      notes: null,
    };
    const out = applyDiscount(100, inactive);
    assert.equal(out.fare, 100);
    assert.equal(out.discountApplied, false);
  });

  it("applies only active discount rules from data", () => {
    const active: DiscountRule = {
      id: "y",
      type: "senior",
      percent: 20,
      requires_validation: true,
      active: true,
      notes: null,
    };
    const out = applyDiscount(100, active);
    assert.equal(out.fare, 80);
    assert.equal(out.discountApplied, true);
    assert.equal(out.discountType, "senior");
  });
});
