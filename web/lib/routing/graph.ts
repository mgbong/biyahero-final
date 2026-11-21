/**
 * Build a stops-and-routes graph for pathfinding.
 * Ride edges: forward along each route (consecutive stops).
 * Walk edges: from transfers table + optional access walks to pins.
 */

import { estimateSegmentFare, pickFareRule } from "@/lib/fare/estimate";
import { haversineMeters, vehicleSpeedMps, walkSeconds } from "@/lib/geo/haversine";
import type {
  FareRule,
  Route,
  RouteStop,
  Stop,
  Transfer,
} from "@/lib/types/database";
import type { GraphEdge, TransitGraph } from "@/lib/routing/types";

export type NetworkInput = {
  stops: Stop[];
  routes: Route[];
  routeStops: RouteStop[];
  transfers: Transfer[];
  fareRules: FareRule[];
};

const ORIGIN_ID = "__origin__";
const DEST_ID = "__dest__";

export { ORIGIN_ID, DEST_ID };

export function buildTransitGraph(input: NetworkInput): TransitGraph {
  const stopName: Record<string, string> = {};
  const stopCoord: Record<string, [number, number]> = {};
  const outgoing = new Map<string, GraphEdge[]>();

  for (const s of input.stops) {
    stopName[s.id] = s.name;
    stopCoord[s.id] = s.geom.coordinates;
    outgoing.set(s.id, []);
  }

  const routeById = new Map(input.routes.filter((r) => r.active).map((r) => [r.id, r]));

  // Group route_stops by route, sorted by sequence
  const byRoute = new Map<string, RouteStop[]>();
  for (const rs of input.routeStops) {
    if (!routeById.has(rs.route_id)) continue;
    const list = byRoute.get(rs.route_id) ?? [];
    list.push(rs);
    byRoute.set(rs.route_id, list);
  }

  for (const [routeId, seq] of byRoute) {
    seq.sort((a, b) => a.sequence - b.sequence);
    const route = routeById.get(routeId)!;
    for (let i = 0; i < seq.length - 1; i++) {
      const a = seq[i];
      const b = seq[i + 1];
      const from = stopCoord[a.stop_id];
      const to = stopCoord[b.stop_id];
      if (!from || !to) continue;
      const distanceM = haversineMeters(from, to);
      const speed = vehicleSpeedMps(route.transport_type);
      const timeSec = Math.max(30, Math.round(distanceM / speed));
      const rule = pickFareRule(input.fareRules, route.transport_type);
      const fare = estimateSegmentFare(rule, distanceM);
      const edge: GraphEdge = {
        id: `ride:${routeId}:${a.stop_id}->${b.stop_id}`,
        fromStopId: a.stop_id,
        toStopId: b.stop_id,
        kind: "ride",
        routeId,
        routeCode: route.code,
        routeName: route.name,
        transportType: route.transport_type,
        distanceM,
        timeSec,
        fare,
        transferIncrement: 1, // boarding counted in Dijkstra when route changes
        walkM: 0,
        verification_status: route.verification_status,
      };
      outgoing.get(a.stop_id)!.push(edge);
    }
  }

  for (const t of input.transfers) {
    if (!outgoing.has(t.from_stop_id) || !outgoing.has(t.to_stop_id)) continue;
    const distanceM = Number(t.walking_distance_m);
    const timeSec =
      t.estimated_walk_seconds ?? walkSeconds(distanceM);
    const edge: GraphEdge = {
      id: `walk:${t.id}`,
      fromStopId: t.from_stop_id,
      toStopId: t.to_stop_id,
      kind: "walk_transfer",
      routeId: null,
      routeCode: null,
      routeName: null,
      transportType: "walk_link",
      distanceM,
      timeSec,
      fare: 0,
      transferIncrement: 0,
      walkM: distanceM,
      verification_status: null,
    };
    outgoing.get(t.from_stop_id)!.push(edge);
  }

  return {
    stopIds: Object.keys(stopCoord),
    stopName,
    stopCoord,
    outgoing,
  };
}

/** Attach temporary origin/destination nodes linked by access walks. */
export function attachAccessNodes(
  base: TransitGraph,
  opts: {
    origin?: { lon: number; lat: number } | null;
    destination?: { lon: number; lat: number } | null;
    originStopId?: string | null;
    destinationStopId?: string | null;
    maxWalkM: number;
  }
): { graph: TransitGraph; originId: string; destId: string } {
  const graph: TransitGraph = {
    stopIds: [...base.stopIds],
    stopName: { ...base.stopName },
    stopCoord: { ...base.stopCoord },
    outgoing: new Map(
      [...base.outgoing.entries()].map(([k, v]) => [k, [...v]])
    ),
  };

  let originId = opts.originStopId ?? "";
  let destId = opts.destinationStopId ?? "";

  if (opts.originStopId && graph.outgoing.has(opts.originStopId)) {
    originId = opts.originStopId;
  } else if (opts.origin) {
    originId = ORIGIN_ID;
    graph.stopName[ORIGIN_ID] = "Your start";
    graph.stopCoord[ORIGIN_ID] = [opts.origin.lon, opts.origin.lat];
    graph.outgoing.set(ORIGIN_ID, []);
    graph.stopIds.push(ORIGIN_ID);
    for (const sid of base.stopIds) {
      const d = haversineMeters(
        [opts.origin.lon, opts.origin.lat],
        graph.stopCoord[sid]
      );
      if (d > opts.maxWalkM) continue;
      graph.outgoing.get(ORIGIN_ID)!.push({
        id: `access:origin->${sid}`,
        fromStopId: ORIGIN_ID,
        toStopId: sid,
        kind: "access_walk",
        routeId: null,
        routeCode: null,
        routeName: null,
        transportType: "walk_link",
        distanceM: d,
        timeSec: walkSeconds(d),
        fare: 0,
        transferIncrement: 0,
        walkM: d,
        verification_status: null,
      });
    }
  }

  if (opts.destinationStopId && graph.outgoing.has(opts.destinationStopId)) {
    destId = opts.destinationStopId;
  } else if (opts.destination) {
    destId = DEST_ID;
    graph.stopName[DEST_ID] = "Your destination";
    graph.stopCoord[DEST_ID] = [opts.destination.lon, opts.destination.lat];
    graph.outgoing.set(DEST_ID, []);
    graph.stopIds.push(DEST_ID);
    for (const sid of base.stopIds) {
      const d = haversineMeters(
        graph.stopCoord[sid],
        [opts.destination.lon, opts.destination.lat]
      );
      if (d > opts.maxWalkM) continue;
      if (!graph.outgoing.has(sid)) graph.outgoing.set(sid, []);
      graph.outgoing.get(sid)!.push({
        id: `access:${sid}->dest`,
        fromStopId: sid,
        toStopId: DEST_ID,
        kind: "access_walk",
        routeId: null,
        routeCode: null,
        routeName: null,
        transportType: "walk_link",
        distanceM: d,
        timeSec: walkSeconds(d),
        fare: 0,
        transferIncrement: 0,
        walkM: d,
        verification_status: null,
      });
    }
  }

  return { graph, originId, destId };
}

export function nearestStopId(
  graph: TransitGraph,
  lon: number,
  lat: number
): string | null {
  let best: string | null = null;
  let bestD = Infinity;
  for (const sid of graph.stopIds) {
    if (sid === ORIGIN_ID || sid === DEST_ID) continue;
    const d = haversineMeters([lon, lat], graph.stopCoord[sid]);
    if (d < bestD) {
      bestD = d;
      best = sid;
    }
  }
  return best;
}
