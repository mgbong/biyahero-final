import { NextResponse } from "next/server";
import { planRoutes } from "@/lib/routing/planner";
import type { PlanCriterion, PlanRequest } from "@/lib/routing/types";

export const dynamic = "force-dynamic";

const CRITERIA = new Set<PlanCriterion>([
  "cheapest",
  "fastest",
  "fewest_transfers",
  "shortest_walk",
]);

export async function POST(req: Request) {
  let body: PlanRequest;
  try {
    body = (await req.json()) as PlanRequest;
  } catch {
    return NextResponse.json(
      { ok: false, alternatives: [], error: "Invalid JSON body." },
      { status: 400 }
    );
  }

  if (body.sortBy && !CRITERIA.has(body.sortBy)) {
    return NextResponse.json(
      { ok: false, alternatives: [], error: "Invalid sortBy criterion." },
      { status: 400 }
    );
  }

  const result = planRoutes(body);
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}
