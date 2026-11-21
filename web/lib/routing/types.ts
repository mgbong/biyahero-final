import type {
  PlanCriterion,
  TransportType,
  VerificationStatus,
} from "@/lib/types/database";

export type EdgeKind = "ride" | "walk_transfer" | "access_walk";

export type GraphEdge = {
  id: string;
  fromStopId: string;
  toStopId: string;
  kind: EdgeKind;
  routeId: string | null;
  routeCode: string | null;
  routeName: string | null;
  transportType: TransportType | null;
  distanceM: number;
  timeSec: number;
  fare: number;
  /** 1 if this edge starts a new vehicle boarding (not continuing same route). */
  transferIncrement: number;
  walkM: number;
  verification_status: VerificationStatus | null;
};

export type TransitGraph = {
  stopIds: string[];
  stopName: Record<string, string>;
  stopCoord: Record<string, [number, number]>; // lon, lat
  outgoing: Map<string, GraphEdge[]>;
};

export type CostWeights = {
  fare: number;
  timeSec: number;
  transfers: number;
  walkM: number;
};

/** Weighted cost used by Dijkstra for a given criterion. */
export const CRITERION_WEIGHTS: Record<PlanCriterion, CostWeights> = {
  cheapest: { fare: 1, timeSec: 0.0001, transfers: 0.5, walkM: 0.00001 },
  fastest: { fare: 0.01, timeSec: 1, transfers: 30, walkM: 0.01 },
  fewest_transfers: { fare: 0.01, timeSec: 0.01, transfers: 1000, walkM: 0.01 },
  shortest_walk: { fare: 0.01, timeSec: 0.01, transfers: 5, walkM: 1 },
};

export type PathMetrics = {
  totalFare: number;
  totalTimeSec: number;
  transfers: number;
  walkM: number;
  rideM: number;
};

export type ItineraryLeg = {
  kind: EdgeKind;
  fromStopId: string;
  fromStopName: string;
  toStopId: string;
  toStopName: string;
  routeId: string | null;
  routeCode: string | null;
  routeName: string | null;
  transportType: TransportType | null;
  distanceM: number;
  timeSec: number;
  fare: number;
  verification_status: VerificationStatus | null;
};

export type ScoredItinerary = {
  id: string;
  labels: PlanCriterion[];
  primaryCriterion: PlanCriterion;
  metrics: PathMetrics;
  legs: ItineraryLeg[];
  summary: string;
};

export type PlanRequest = {
  /** Stop id OR lon/lat pin */
  originStopId?: string;
  destinationStopId?: string;
  origin?: { lon: number; lat: number };
  destination?: { lon: number; lat: number };
  maxWalkM?: number;
  maxTransfers?: number;
  sortBy?: PlanCriterion;
};

export type PlanResponse = {
  ok: boolean;
  alternatives: ScoredItinerary[];
  sortBy: PlanCriterion;
  error?: string;
};
