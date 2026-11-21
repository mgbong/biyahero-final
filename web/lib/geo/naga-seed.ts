/**
 * Local Naga City seed geometry (mirrors supabase/seed/001_naga_sample.sql).
 * Used when Supabase env is missing so Phase 2 map still works.
 */

import type {
  FareRule,
  Route,
  RouteStop,
  Stop,
  Transfer,
  TransportType,
  VerificationStatus,
} from "@/lib/types/database";

export const NAGA_CENTER: [number, number] = [13.6218, 123.1948]; // lat, lon for Leaflet

export type StopFeatureProps = {
  id: string;
  name: string;
  landmark_notes: string | null;
  verification_status: VerificationStatus;
  last_verified_at: string | null;
};

export type RouteFeatureProps = {
  id: string;
  name: string;
  code: string | null;
  transport_type: TransportType;
  verification_status: VerificationStatus;
  last_verified_at: string | null;
  active: boolean;
};

const now = "2026-10-01T00:00:00Z";

export const SEED_STOPS: Stop[] = [
  {
    id: "b1000000-0000-4000-8000-000000000001",
    name: "Naga Metropolitan Cathedral",
    geom: { type: "Point", coordinates: [123.1851, 13.6198] },
    landmark_notes: "Near Plaza Rizal / downtown core",
    verification_status: "verified",
    last_verified_at: now,
    created_at: now,
    updated_at: now,
  },
  {
    id: "b1000000-0000-4000-8000-000000000002",
    name: "SM City Naga",
    geom: { type: "Point", coordinates: [123.2368, 13.6239] },
    landmark_notes: "Mall jeepney bay along CBD II",
    verification_status: "verified",
    last_verified_at: now,
    created_at: now,
    updated_at: now,
  },
  {
    id: "b1000000-0000-4000-8000-000000000003",
    name: "Naga Central Bus Terminal",
    geom: { type: "Point", coordinates: [123.1949, 13.6262] },
    landmark_notes: "Main provincial bus / jeep hub",
    verification_status: "verified",
    last_verified_at: "2026-09-15T00:00:00Z",
    created_at: now,
    updated_at: now,
  },
  {
    id: "b1000000-0000-4000-8000-000000000004",
    name: "Robinsons Place Naga",
    geom: { type: "Point", coordinates: [123.2002, 13.6241] },
    landmark_notes: "Along Roxas Avenue",
    verification_status: "verified",
    last_verified_at: "2026-09-15T00:00:00Z",
    created_at: now,
    updated_at: now,
  },
  {
    id: "b1000000-0000-4000-8000-000000000005",
    name: "University of Nueva Caceres",
    geom: { type: "Point", coordinates: [123.1856, 13.6281] },
    landmark_notes: "UNC main gate, Elias Angeles St",
    verification_status: "pending_verification",
    last_verified_at: null,
    created_at: now,
    updated_at: now,
  },
  {
    id: "b1000000-0000-4000-8000-000000000006",
    name: "Magsaysay Avenue Junction",
    geom: { type: "Point", coordinates: [123.1904, 13.6212] },
    landmark_notes: "Busy transfer strip toward downtown",
    verification_status: "verified",
    last_verified_at: "2026-08-20T00:00:00Z",
    created_at: now,
    updated_at: now,
  },
  {
    id: "b1000000-0000-4000-8000-000000000007",
    name: "Concepcion Pequeña Crossing",
    geom: { type: "Point", coordinates: [123.2055, 13.6108] },
    landmark_notes: "South corridor jeep stop",
    verification_status: "potentially_outdated",
    last_verified_at: "2025-11-01T00:00:00Z",
    created_at: now,
    updated_at: now,
  },
  {
    id: "b1000000-0000-4000-8000-000000000008",
    name: "Camaligan Public Market",
    geom: { type: "Point", coordinates: [123.1702, 13.6305] },
    landmark_notes: "West of Naga toward Camaligan",
    verification_status: "pending_verification",
    last_verified_at: null,
    created_at: now,
    updated_at: now,
  },
];

export const SEED_ROUTES: Route[] = [
  {
    id: "a1000000-0000-4000-8000-000000000001",
    name: "Cathedral – SM City Jeep",
    code: "NGA-01",
    transport_type: "jeepney",
    geom: {
      type: "LineString",
      coordinates: [
        [123.1851, 13.6198],
        [123.1904, 13.6212],
        [123.2002, 13.6241],
        [123.2368, 13.6239],
      ],
    },
    verification_status: "verified",
    last_verified_at: now,
    active: true,
    created_at: now,
    updated_at: now,
  },
  {
    id: "a1000000-0000-4000-8000-000000000002",
    name: "Terminal – Robinsons – Concepcion",
    code: "NGA-02",
    transport_type: "jeepney",
    geom: {
      type: "LineString",
      coordinates: [
        [123.1949, 13.6262],
        [123.2002, 13.6241],
        [123.2055, 13.6108],
      ],
    },
    verification_status: "verified",
    last_verified_at: "2026-09-15T00:00:00Z",
    active: true,
    created_at: now,
    updated_at: now,
  },
  {
    id: "a1000000-0000-4000-8000-000000000003",
    name: "UNC – Cathedral – Camaligan Tricycle",
    code: "NGA-TRI-01",
    transport_type: "tricycle",
    geom: {
      type: "LineString",
      coordinates: [
        [123.1856, 13.6281],
        [123.1851, 13.6198],
        [123.1702, 13.6305],
      ],
    },
    verification_status: "pending_verification",
    last_verified_at: null,
    active: true,
    created_at: now,
    updated_at: now,
  },
  {
    id: "a1000000-0000-4000-8000-000000000004",
    name: "Terminal – SM Express Bus Shuttle",
    code: "NGA-BUS-01",
    transport_type: "bus",
    geom: {
      type: "LineString",
      coordinates: [
        [123.1949, 13.6262],
        [123.2002, 13.6241],
        [123.2368, 13.6239],
      ],
    },
    verification_status: "potentially_outdated",
    last_verified_at: "2025-12-01T00:00:00Z",
    active: true,
    created_at: now,
    updated_at: now,
  },
];

export const SEED_ROUTE_STOPS: RouteStop[] = [
  // NGA-01
  { route_id: "a1000000-0000-4000-8000-000000000001", stop_id: "b1000000-0000-4000-8000-000000000001", sequence: 1 },
  { route_id: "a1000000-0000-4000-8000-000000000001", stop_id: "b1000000-0000-4000-8000-000000000006", sequence: 2 },
  { route_id: "a1000000-0000-4000-8000-000000000001", stop_id: "b1000000-0000-4000-8000-000000000004", sequence: 3 },
  { route_id: "a1000000-0000-4000-8000-000000000001", stop_id: "b1000000-0000-4000-8000-000000000002", sequence: 4 },
  // NGA-02
  { route_id: "a1000000-0000-4000-8000-000000000002", stop_id: "b1000000-0000-4000-8000-000000000003", sequence: 1 },
  { route_id: "a1000000-0000-4000-8000-000000000002", stop_id: "b1000000-0000-4000-8000-000000000004", sequence: 2 },
  { route_id: "a1000000-0000-4000-8000-000000000002", stop_id: "b1000000-0000-4000-8000-000000000007", sequence: 3 },
  // NGA-TRI-01
  { route_id: "a1000000-0000-4000-8000-000000000003", stop_id: "b1000000-0000-4000-8000-000000000005", sequence: 1 },
  { route_id: "a1000000-0000-4000-8000-000000000003", stop_id: "b1000000-0000-4000-8000-000000000001", sequence: 2 },
  { route_id: "a1000000-0000-4000-8000-000000000003", stop_id: "b1000000-0000-4000-8000-000000000008", sequence: 3 },
  // NGA-BUS-01
  { route_id: "a1000000-0000-4000-8000-000000000004", stop_id: "b1000000-0000-4000-8000-000000000003", sequence: 1 },
  { route_id: "a1000000-0000-4000-8000-000000000004", stop_id: "b1000000-0000-4000-8000-000000000004", sequence: 2 },
  { route_id: "a1000000-0000-4000-8000-000000000004", stop_id: "b1000000-0000-4000-8000-000000000002", sequence: 3 },
];

export const SEED_TRANSFERS: Transfer[] = [
  {
    id: "c1000000-0000-4000-8000-000000000001",
    from_stop_id: "b1000000-0000-4000-8000-000000000001",
    to_stop_id: "b1000000-0000-4000-8000-000000000006",
    walking_distance_m: 650,
    estimated_walk_seconds: 480,
  },
  {
    id: "c1000000-0000-4000-8000-000000000002",
    from_stop_id: "b1000000-0000-4000-8000-000000000006",
    to_stop_id: "b1000000-0000-4000-8000-000000000001",
    walking_distance_m: 650,
    estimated_walk_seconds: 480,
  },
  {
    id: "c1000000-0000-4000-8000-000000000003",
    from_stop_id: "b1000000-0000-4000-8000-000000000003",
    to_stop_id: "b1000000-0000-4000-8000-000000000004",
    walking_distance_m: 900,
    estimated_walk_seconds: 660,
  },
  {
    id: "c1000000-0000-4000-8000-000000000004",
    from_stop_id: "b1000000-0000-4000-8000-000000000004",
    to_stop_id: "b1000000-0000-4000-8000-000000000003",
    walking_distance_m: 900,
    estimated_walk_seconds: 660,
  },
];

export const SEED_FARE_RULES: FareRule[] = [
  {
    id: "d1000000-0000-4000-8000-000000000001",
    transport_type: "jeepney",
    base_fare: 13,
    per_km_rate: 1.8,
    min_fare: 13,
    currency: "PHP",
    active: true,
    effective_from: "2026-01-01T00:00:00Z",
    effective_to: null,
  },
  {
    id: "d1000000-0000-4000-8000-000000000002",
    transport_type: "tricycle",
    base_fare: 20,
    per_km_rate: 5,
    min_fare: 20,
    currency: "PHP",
    active: true,
    effective_from: "2026-01-01T00:00:00Z",
    effective_to: null,
  },
  {
    id: "d1000000-0000-4000-8000-000000000003",
    transport_type: "bus",
    base_fare: 15,
    per_km_rate: 2.2,
    min_fare: 15,
    currency: "PHP",
    active: true,
    effective_from: "2026-01-01T00:00:00Z",
    effective_to: null,
  },
];

export function stopsToGeoJSON(stops: Stop[]) {
  return {
    type: "FeatureCollection" as const,
    features: stops.map((s) => ({
      type: "Feature" as const,
      geometry: s.geom,
      properties: {
        id: s.id,
        name: s.name,
        landmark_notes: s.landmark_notes,
        verification_status: s.verification_status,
        last_verified_at: s.last_verified_at,
      } satisfies StopFeatureProps,
    })),
  };
}

export function routesToGeoJSON(routes: Route[]) {
  return {
    type: "FeatureCollection" as const,
    features: routes
      .filter((r) => r.geom && r.active)
      .map((r) => ({
        type: "Feature" as const,
        geometry: r.geom!,
        properties: {
          id: r.id,
          name: r.name,
          code: r.code,
          transport_type: r.transport_type,
          verification_status: r.verification_status,
          last_verified_at: r.last_verified_at,
          active: r.active,
        } satisfies RouteFeatureProps,
      })),
  };
}
