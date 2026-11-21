/**
 * Multi-criteria route planner: runs Dijkstra per criterion, labels winners,
 * returns alternatives the UI can sort/switch.
 */

import {
  SEED_FARE_RULES,
  SEED_ROUTES,
  SEED_ROUTE_STOPS,
  SEED_STOPS,
  SEED_TRANSFERS,
} from "@/lib/geo/naga-seed";
import { attachAccessNodes, buildTransitGraph } from "@/lib/routing/graph";
import { dijkstra } from "@/lib/routing/dijkstra";
import type {
  CostWeights,
  ItineraryLeg,
  PlanCriterion,
  PlanRequest,
  PlanResponse,
  ScoredItinerary,
  TransitGraph,
} from "@/lib/routing/types";
import { CRITERION_WEIGHTS } from "@/lib/routing/types";
import type { NetworkInput } from "@/lib/routing/graph";

const CRITERIA: PlanCriterion[] = [
  "cheapest",
  "fastest",
  "fewest_transfers",
  "shortest_walk",
];

export function defaultNetwork(): NetworkInput {
  return {
    stops: SEED_STOPS,
    routes: SEED_ROUTES,
    routeStops: SEED_ROUTE_STOPS,
    transfers: SEED_TRANSFERS,
    fareRules: SEED_FARE_RULES,
  };
}

function pathSignature(edges: { id: string }[]): string {
  return edges.map((e) => e.id).join(">");
}

function legsFrom(
  graph: TransitGraph,
  edges: import("@/lib/routing/types").GraphEdge[]
): ItineraryLeg[] {
  return edges.map((e) => ({
    kind: e.kind,
    fromStopId: e.fromStopId,
    fromStopName: graph.stopName[e.fromStopId] ?? e.fromStopId,
    toStopId: e.toStopId,
    toStopName: graph.stopName[e.toStopId] ?? e.toStopId,
    routeId: e.routeId,
    routeCode: e.routeCode,
    routeName: e.routeName,
    transportType: e.transportType,
    distanceM: Math.round(e.distanceM),
    timeSec: e.timeSec,
    fare: e.fare,
    verification_status: e.verification_status,
  }));
}

function summarize(legs: ItineraryLeg[], criterion: PlanCriterion): string {
  const rides = legs.filter((l) => l.kind === "ride");
  const codes = rides.map((r) => r.routeCode ?? r.routeName ?? "ride");
  const unique = [...new Set(codes)];
  const label =
    criterion === "cheapest"
      ? "Cheapest"
      : criterion === "fastest"
        ? "Fastest"
        : criterion === "fewest_transfers"
          ? "Fewest transfers"
          : "Shortest walk";
  return `${label}: ${unique.join(" → ") || "walk only"}`;
}

function metricValue(m: ScoredItinerary["metrics"], c: PlanCriterion): number {
  switch (c) {
    case "cheapest":
      return m.totalFare;
    case "fastest":
      return m.totalTimeSec;
    case "fewest_transfers":
      return m.transfers * 1e6 + m.totalTimeSec;
    case "shortest_walk":
      return m.walkM;
  }
}

export function planRoutes(
  req: PlanRequest,
  network: NetworkInput = defaultNetwork()
): PlanResponse {
  const sortBy = req.sortBy ?? "fastest";
  const maxWalkM = req.maxWalkM ?? 1200;
  const maxTransfers = req.maxTransfers ?? 3;

  if (
    !req.originStopId &&
    !req.origin &&
    !req.destinationStopId &&
    !req.destination
  ) {
    return {
      ok: false,
      alternatives: [],
      sortBy,
      error: "Provide origin and destination (stop id or lon/lat).",
    };
  }

  if (
    (!req.originStopId && !req.origin) ||
    (!req.destinationStopId && !req.destination)
  ) {
    return {
      ok: false,
      alternatives: [],
      sortBy,
      error: "Both origin and destination are required.",
    };
  }

  const base = buildTransitGraph(network);
  const { graph, originId, destId } = attachAccessNodes(base, {
    origin: req.origin ?? null,
    destination: req.destination ?? null,
    originStopId: req.originStopId ?? null,
    destinationStopId: req.destinationStopId ?? null,
    maxWalkM,
  });

  if (!originId || !destId) {
    return {
      ok: false,
      alternatives: [],
      sortBy,
      error: "Could not resolve origin or destination.",
    };
  }

  if (originId === destId) {
    return {
      ok: false,
      alternatives: [],
      sortBy,
      error: "Origin and destination are the same.",
    };
  }

  // Ensure access edges exist when using stop IDs only
  if (!graph.outgoing.has(originId)) {
    return {
      ok: false,
      alternatives: [],
      sortBy,
      error: "Unknown origin stop.",
    };
  }

  const bySig = new Map<string, ScoredItinerary>();
  const bestFor = new Map<PlanCriterion, string>();

  for (const criterion of CRITERIA) {
    const weights: CostWeights = CRITERION_WEIGHTS[criterion];
    const result = dijkstra(graph, originId, destId, weights, {
      maxTransfers,
    });
    if (!result || !result.edges.length) continue;

    const sig = pathSignature(result.edges);
    const legs = legsFrom(graph, result.edges);
    const existing = bySig.get(sig);
    if (existing) {
      if (!existing.labels.includes(criterion)) existing.labels.push(criterion);
    } else {
      const item: ScoredItinerary = {
        id: `itin_${bySig.size + 1}`,
        labels: [criterion],
        primaryCriterion: criterion,
        metrics: result.metrics,
        legs,
        summary: summarize(legs, criterion),
      };
      bySig.set(sig, item);
    }
    bestFor.set(criterion, sig);
  }

  // Tag which criteria each path wins (recompute by metric among unique paths)
  const alts = [...bySig.values()];
  for (const c of CRITERIA) {
    let winner: ScoredItinerary | null = null;
    let best = Infinity;
    for (const a of alts) {
      const v = metricValue(a.metrics, c);
      if (v < best) {
        best = v;
        winner = a;
      }
    }
    if (winner && !winner.labels.includes(c)) winner.labels.push(c);
  }

  // Set primaryCriterion from sort preference when labeled, else first label
  for (const a of alts) {
    if (a.labels.includes(sortBy)) a.primaryCriterion = sortBy;
    else a.primaryCriterion = a.labels[0] ?? sortBy;
    a.summary = summarize(a.legs, a.primaryCriterion);
  }

  alts.sort((a, b) => {
    const va = metricValue(a.metrics, sortBy);
    const vb = metricValue(b.metrics, sortBy);
    if (va !== vb) return va - vb;
    return a.metrics.totalTimeSec - b.metrics.totalTimeSec;
  });

  if (!alts.length) {
    return {
      ok: false,
      alternatives: [],
      sortBy,
      error:
        "No route found within walk/transfer limits. Try a longer max walk or more transfers.",
    };
  }

  void bestFor;
  return { ok: true, alternatives: alts, sortBy };
}
