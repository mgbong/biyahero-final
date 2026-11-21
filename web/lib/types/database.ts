/** Shared DB / domain types for BIYAHERO (mirrors supabase migrations). */

export type VerificationStatus =
  | "verified"
  | "pending_verification"
  | "potentially_outdated";

export type TransportType = "jeepney" | "tricycle" | "bus" | "walk_link";

export type PlanCriterion =
  | "cheapest"
  | "fastest"
  | "fewest_transfers"
  | "shortest_walk";

export type GeoPoint = {
  type: "Point";
  coordinates: [number, number]; // [lon, lat]
};

export type GeoLineString = {
  type: "LineString";
  coordinates: [number, number][];
};

export type Stop = {
  id: string;
  name: string;
  geom: GeoPoint;
  landmark_notes: string | null;
  verification_status: VerificationStatus;
  last_verified_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Route = {
  id: string;
  name: string;
  code: string | null;
  transport_type: TransportType;
  geom: GeoLineString | null;
  verification_status: VerificationStatus;
  last_verified_at: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type RouteStop = {
  route_id: string;
  stop_id: string;
  sequence: number;
};

export type Transfer = {
  id: string;
  from_stop_id: string;
  to_stop_id: string;
  walking_distance_m: number;
  estimated_walk_seconds: number | null;
};

export type FareRule = {
  id: string;
  transport_type: TransportType;
  base_fare: number;
  per_km_rate: number;
  min_fare: number | null;
  currency: string;
  active: boolean;
  effective_from: string | null;
  effective_to: string | null;
};

export type DiscountRule = {
  id: string;
  type: string;
  percent: number;
  requires_validation: boolean;
  active: boolean;
  notes: string | null;
};

export type Disruption = {
  id: string;
  title: string;
  description: string;
  disruption_kind: string | null;
  affected_route_ids: string[];
  affected_stop_ids: string[];
  starts_at: string;
  ends_at: string | null;
  verified: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};
