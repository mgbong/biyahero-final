import { NextResponse } from "next/server";
import { loadGeoBundle } from "@/lib/geo/fetch-network";

export const dynamic = "force-dynamic";

/** GET /api/geo/network — stops + routes GeoJSON for the map. */
export async function GET() {
  const bundle = await loadGeoBundle();
  return NextResponse.json({
    ok: true,
    source: bundle.source,
    stops: bundle.stops,
    routes: bundle.routes,
  });
}
