/**
 * Load stops/routes from Supabase when configured; else local Naga seed.
 */

import { createClient } from "@supabase/supabase-js";
import type { Route, Stop } from "@/lib/types/database";
import {
  SEED_ROUTES,
  SEED_STOPS,
  routesToGeoJSON,
  stopsToGeoJSON,
} from "@/lib/geo/naga-seed";

export type GeoBundle = {
  source: "supabase" | "seed";
  stops: ReturnType<typeof stopsToGeoJSON>;
  routes: ReturnType<typeof routesToGeoJSON>;
};

function hasSupabaseEnv() {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL &&
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  );
}

/** Parse GeoJSON / WKT-ish payloads Supabase may return via RPC or JSON columns. */
function asPoint(
  geom: unknown,
  lon?: number,
  lat?: number
): Stop["geom"] | null {
  if (
    geom &&
    typeof geom === "object" &&
    "type" in geom &&
    (geom as { type: string }).type === "Point" &&
    "coordinates" in geom
  ) {
    return geom as Stop["geom"];
  }
  if (typeof lon === "number" && typeof lat === "number") {
    return { type: "Point", coordinates: [lon, lat] };
  }
  return null;
}

function asLine(geom: unknown): Route["geom"] | null {
  if (
    geom &&
    typeof geom === "object" &&
    "type" in geom &&
    (geom as { type: string }).type === "LineString" &&
    "coordinates" in geom
  ) {
    return geom as Route["geom"];
  }
  return null;
}

async function fetchFromSupabase(): Promise<GeoBundle | null> {
  if (!hasSupabaseEnv()) return null;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
  const sb = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  // Prefer GeoJSON views from migration 002; fall back to seed on failure.
  const { data: stopRows, error: stopErr } = await sb
    .from("stops_geojson")
    .select(
      "id, name, landmark_notes, verification_status, last_verified_at, created_at, updated_at, geom_geojson"
    );

  const { data: routeRows, error: routeErr } = await sb
    .from("routes_geojson")
    .select(
      "id, name, code, transport_type, verification_status, last_verified_at, active, created_at, updated_at, geom_geojson"
    )
    .eq("active", true);

  if (stopErr || routeErr || !stopRows?.length) {
    return null;
  }

  const stops: Stop[] = [];
  for (const row of stopRows) {
    const r = row as Record<string, unknown>;
    const geom = asPoint(r.geom_geojson ?? r.geom);
    if (!geom) continue;
    stops.push({
      id: String(r.id),
      name: String(r.name),
      geom,
      landmark_notes: (r.landmark_notes as string | null) ?? null,
      verification_status: r.verification_status as Stop["verification_status"],
      last_verified_at: (r.last_verified_at as string | null) ?? null,
      created_at: String(r.created_at ?? ""),
      updated_at: String(r.updated_at ?? ""),
    });
  }

  const routes: Route[] = [];
  for (const row of routeRows ?? []) {
    const r = row as Record<string, unknown>;
    const geom = asLine(r.geom_geojson ?? r.geom);
    routes.push({
      id: String(r.id),
      name: String(r.name),
      code: (r.code as string | null) ?? null,
      transport_type: r.transport_type as Route["transport_type"],
      geom,
      verification_status: r.verification_status as Route["verification_status"],
      last_verified_at: (r.last_verified_at as string | null) ?? null,
      active: Boolean(r.active),
      created_at: String(r.created_at ?? ""),
      updated_at: String(r.updated_at ?? ""),
    });
  }

  if (!stops.length) return null;

  return {
    source: "supabase",
    stops: stopsToGeoJSON(stops),
    routes: routesToGeoJSON(routes),
  };
}

export async function loadGeoBundle(): Promise<GeoBundle> {
  try {
    const remote = await fetchFromSupabase();
    if (remote) return remote;
  } catch {
    // fall through to seed
  }

  return {
    source: "seed",
    stops: stopsToGeoJSON(SEED_STOPS),
    routes: routesToGeoJSON(SEED_ROUTES),
  };
}
