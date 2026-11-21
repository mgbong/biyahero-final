/**
 * Dijkstra over (stop, lastRouteId, boardings) so continuing the same vehicle
 * does not count as a new transfer.
 */

import type {
  CostWeights,
  GraphEdge,
  PathMetrics,
  TransitGraph,
} from "@/lib/routing/types";

export type PathResult = {
  edges: GraphEdge[];
  metrics: PathMetrics;
  cost: number;
};

function edgeCost(edge: GraphEdge, w: CostWeights, isNewBoarding: boolean): number {
  const transferInc = isNewBoarding ? 1 : 0;
  return (
    w.fare * edge.fare +
    w.timeSec * edge.timeSec +
    w.transfers * transferInc +
    w.walkM * edge.walkM
  );
}

class MinHeap {
  private data: { key: string; cost: number }[] = [];

  push(key: string, cost: number) {
    this.data.push({ key, cost });
    this.bubbleUp(this.data.length - 1);
  }

  pop(): { key: string; cost: number } | undefined {
    if (!this.data.length) return undefined;
    const top = this.data[0];
    const last = this.data.pop()!;
    if (this.data.length) {
      this.data[0] = last;
      this.bubbleDown(0);
    }
    return top;
  }

  get size() {
    return this.data.length;
  }

  private bubbleUp(i: number) {
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (this.data[p].cost <= this.data[i].cost) break;
      [this.data[p], this.data[i]] = [this.data[i], this.data[p]];
      i = p;
    }
  }

  private bubbleDown(i: number) {
    for (;;) {
      const l = i * 2 + 1;
      const r = l + 1;
      let sm = i;
      if (l < this.data.length && this.data[l].cost < this.data[sm].cost) sm = l;
      if (r < this.data.length && this.data[r].cost < this.data[sm].cost) sm = r;
      if (sm === i) break;
      [this.data[sm], this.data[i]] = [this.data[i], this.data[sm]];
      i = sm;
    }
  }
}

/**
 * @param maxTransfers — max vehicle changes after the first boarding (0 = direct only).
 */
export function dijkstra(
  graph: TransitGraph,
  originId: string,
  destId: string,
  weights: CostWeights,
  opts?: { maxTransfers?: number }
): PathResult | null {
  if (!originId || !destId || !graph.outgoing.has(originId)) return null;

  const maxTransfers = opts?.maxTransfers ?? 5;
  const maxBoardings = maxTransfers + 1;

  type Ext = { stopId: string; lastRouteId: string; boardings: number };
  const keyOf = (s: Ext) => `${s.stopId}|${s.lastRouteId}|${s.boardings}`;

  const heap = new MinHeap();
  const best = new Map<string, number>();
  const prev = new Map<
    string,
    { prevKey: string | null; edge: GraphEdge | null }
  >();

  const start: Ext = { stopId: originId, lastRouteId: "", boardings: 0 };
  const sk = keyOf(start);
  best.set(sk, 0);
  prev.set(sk, { prevKey: null, edge: null });
  heap.push(sk, 0);

  let goalKey: string | null = null;

  while (heap.size) {
    const cur = heap.pop()!;
    const costSoFar = best.get(cur.key);
    if (costSoFar == null || cur.cost > costSoFar) continue;

    const [stopId, lastRouteId, boardingsStr] = cur.key.split("|");
    const boardings = Number(boardingsStr);
    if (stopId === destId) {
      goalKey = cur.key;
      break;
    }

    for (const edge of graph.outgoing.get(stopId) ?? []) {
      const isNewBoarding =
        edge.kind === "ride" && !!edge.routeId && edge.routeId !== lastRouteId;
      const nextBoardings = boardings + (isNewBoarding ? 1 : 0);
      if (nextBoardings > maxBoardings) continue;

      const step = edgeCost(edge, weights, isNewBoarding);
      const nextCost = costSoFar + step;
      const nextLast =
        edge.kind === "ride" && edge.routeId ? edge.routeId : "";

      const nk = keyOf({
        stopId: edge.toStopId,
        lastRouteId: nextLast,
        boardings: nextBoardings,
      });

      if (nextCost + 1e-9 < (best.get(nk) ?? Infinity)) {
        best.set(nk, nextCost);
        prev.set(nk, { prevKey: cur.key, edge });
        heap.push(nk, nextCost);
      }
    }
  }

  if (!goalKey) return null;

  const edges: GraphEdge[] = [];
  let cursor: string | null = goalKey;
  while (cursor) {
    const p = prev.get(cursor);
    if (!p) break;
    if (p.edge) edges.push(p.edge);
    cursor = p.prevKey;
  }
  edges.reverse();

  return {
    edges,
    metrics: metricsFromEdges(edges),
    cost: best.get(goalKey) ?? 0,
  };
}

export function metricsFromEdges(edges: GraphEdge[]): PathMetrics {
  let totalFare = 0;
  let totalTimeSec = 0;
  let walkM = 0;
  let rideM = 0;
  let boardings = 0;
  let lastRoute: string | null = null;

  for (const e of edges) {
    totalFare += e.fare;
    totalTimeSec += e.timeSec;
    walkM += e.walkM;
    if (e.kind === "ride") {
      rideM += e.distanceM;
      if (e.routeId !== lastRoute) {
        boardings += 1;
        lastRoute = e.routeId;
      }
    } else {
      lastRoute = null;
    }
  }

  return {
    totalFare: Math.round(totalFare * 100) / 100,
    totalTimeSec,
    transfers: Math.max(0, boardings - 1),
    walkM: Math.round(walkM),
    rideM: Math.round(rideM),
  };
}
