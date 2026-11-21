import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { planRoutes } from "../../lib/routing/planner";
import { buildTransitGraph } from "../../lib/routing/graph";
import { dijkstra } from "../../lib/routing/dijkstra";
import { CRITERION_WEIGHTS } from "../../lib/routing/types";
import { defaultNetwork } from "../../lib/routing/planner";

describe("multi-criteria planner", () => {
  it("returns alternatives from Cathedral to SM City", () => {
    const res = planRoutes({
      originStopId: "b1000000-0000-4000-8000-000000000001",
      destinationStopId: "b1000000-0000-4000-8000-000000000002",
      sortBy: "fastest",
      maxTransfers: 3,
    });
    assert.equal(res.ok, true);
    assert.ok(res.alternatives.length >= 1);
    const first = res.alternatives[0];
    assert.ok(first.legs.some((l) => l.kind === "ride"));
    assert.ok(first.metrics.totalFare > 0);
    assert.ok(first.metrics.totalTimeSec > 0);
  });

  it("labels at least one criterion on each alternative", () => {
    const res = planRoutes({
      originStopId: "b1000000-0000-4000-8000-000000000005",
      destinationStopId: "b1000000-0000-4000-8000-000000000008",
      sortBy: "fewest_transfers",
    });
    assert.equal(res.ok, true);
    for (const a of res.alternatives) {
      assert.ok(a.labels.length >= 1);
    }
  });

  it("sorts by cheapest when requested", () => {
    const res = planRoutes({
      originStopId: "b1000000-0000-4000-8000-000000000003",
      destinationStopId: "b1000000-0000-4000-8000-000000000002",
      sortBy: "cheapest",
      maxTransfers: 3,
    });
    assert.equal(res.ok, true);
    for (let i = 1; i < res.alternatives.length; i++) {
      assert.ok(
        res.alternatives[i - 1].metrics.totalFare <=
          res.alternatives[i].metrics.totalFare + 1e-6
      );
    }
  });

  it("rejects missing endpoints", () => {
    const res = planRoutes({ sortBy: "fastest" });
    assert.equal(res.ok, false);
    assert.ok(res.error);
  });
});

describe("dijkstra graph", () => {
  it("finds a path on the seed graph", () => {
    const g = buildTransitGraph(defaultNetwork());
    const path = dijkstra(
      g,
      "b1000000-0000-4000-8000-000000000001",
      "b1000000-0000-4000-8000-000000000002",
      CRITERION_WEIGHTS.fastest,
      { maxTransfers: 3 }
    );
    assert.ok(path);
    assert.ok(path!.edges.length >= 1);
    assert.equal(path!.metrics.transfers >= 0, true);
  });
});
