"use client";

import { useMemo, useState } from "react";
import { SEED_STOPS } from "@/lib/geo/naga-seed";
import { verificationBadgeClass, verificationLabel } from "@/lib/geo/verification";
import type { PlanCriterion, ScoredItinerary } from "@/lib/routing/types";

const CRITERIA: { value: PlanCriterion; label: string }[] = [
  { value: "fastest", label: "Fastest" },
  { value: "cheapest", label: "Cheapest" },
  { value: "fewest_transfers", label: "Fewest transfers" },
  { value: "shortest_walk", label: "Shortest walk" },
];

function formatTime(sec: number): string {
  const m = Math.round(sec / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  return `${h} h ${m % 60} min`;
}

function criterionChip(c: PlanCriterion): string {
  return CRITERIA.find((x) => x.value === c)?.label ?? c;
}

export default function PlanForm() {
  const stops = useMemo(
    () => [...SEED_STOPS].sort((a, b) => a.name.localeCompare(b.name)),
    []
  );
  const [originStopId, setOriginStopId] = useState(stops[0]?.id ?? "");
  const [destinationStopId, setDestinationStopId] = useState(
    stops[1]?.id ?? ""
  );
  const [sortBy, setSortBy] = useState<PlanCriterion>("fastest");
  const [maxTransfers, setMaxTransfers] = useState(3);
  const [maxWalkM, setMaxWalkM] = useState(1200);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ScoredItinerary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = results.find((r) => r.id === selectedId) ?? results[0];

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          originStopId,
          destinationStopId,
          sortBy,
          maxTransfers,
          maxWalkM,
        }),
      });
      const data = await res.json();
      if (!data.ok) {
        setResults([]);
        setSelectedId(null);
        setError(data.error || "No routes found.");
        return;
      }
      setResults(data.alternatives ?? []);
      setSelectedId(data.alternatives?.[0]?.id ?? null);
    } catch {
      setError("Could not reach the planner. Try again.");
    } finally {
      setLoading(false);
    }
  }

  function resort(next: PlanCriterion) {
    setSortBy(next);
    setResults((prev) => {
      const copy = [...prev];
      copy.sort((a, b) => {
        const pick = (m: ScoredItinerary["metrics"]) => {
          if (next === "cheapest") return m.totalFare;
          if (next === "fastest") return m.totalTimeSec;
          if (next === "fewest_transfers")
            return m.transfers * 1e6 + m.totalTimeSec;
          return m.walkM;
        };
        return pick(a.metrics) - pick(b.metrics);
      });
      return copy;
    });
  }

  return (
    <div className="flex w-full max-w-3xl flex-col gap-6">
      <form
        onSubmit={onSubmit}
        className="flex flex-col gap-4 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
        aria-labelledby="plan-form-title"
      >
        <div>
          <h1
            id="plan-form-title"
            className="text-2xl font-bold tracking-tight text-[var(--color-text)]"
          >
            Plan a trip
          </h1>
          <p className="mt-1 text-sm text-[var(--color-muted)]">
            Pick stops in Naga. Alternatives are labeled by cheapest, fastest,
            fewest transfers, and shortest walk.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <label className="flex min-w-[200px] flex-1 flex-col gap-1 text-sm">
            <span className="font-semibold">From</span>
            <select
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-page)] px-3 py-2"
              value={originStopId}
              onChange={(e) => setOriginStopId(e.target.value)}
              required
            >
              {stops.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[200px] flex-1 flex-col gap-1 text-sm">
            <span className="font-semibold">To</span>
            <select
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-page)] px-3 py-2"
              value={destinationStopId}
              onChange={(e) => setDestinationStopId(e.target.value)}
              required
            >
              {stops.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="flex flex-wrap gap-3">
          <label className="flex min-w-[140px] flex-1 flex-col gap-1 text-sm">
            <span className="font-semibold">Sort by</span>
            <select
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-page)] px-3 py-2"
              value={sortBy}
              onChange={(e) => resort(e.target.value as PlanCriterion)}
            >
              {CRITERIA.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[120px] flex-1 flex-col gap-1 text-sm">
            <span className="font-semibold">Max transfers</span>
            <select
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-page)] px-3 py-2"
              value={maxTransfers}
              onChange={(e) => setMaxTransfers(Number(e.target.value))}
            >
              {[0, 1, 2, 3].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-[120px] flex-1 flex-col gap-1 text-sm">
            <span className="font-semibold">Max walk</span>
            <select
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-page)] px-3 py-2"
              value={maxWalkM}
              onChange={(e) => setMaxWalkM(Number(e.target.value))}
            >
              <option value={800}>800 m</option>
              <option value={1200}>1.2 km</option>
              <option value={1800}>1.8 km</option>
            </select>
          </label>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="inline-flex w-fit items-center rounded-full bg-[var(--color-accent)] px-5 py-2.5 text-sm font-bold text-white hover:brightness-95 disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
        >
          {loading ? "Finding routes…" : "Find routes"}
        </button>

        {error && (
          <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">
            {error}
          </p>
        )}
      </form>

      {results.length > 0 && (
        <section className="flex flex-col gap-3" aria-label="Route alternatives">
          <h2 className="text-lg font-bold">Alternatives</h2>
          <ul className="flex flex-col gap-2">
            {results.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(r.id)}
                  className={`flex w-full flex-col gap-2 rounded-2xl border px-4 py-3 text-left transition ${
                    selected?.id === r.id
                      ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                      : "border-[var(--color-border)] bg-[var(--color-surface)]"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    {r.labels.map((l) => (
                      <span
                        key={l}
                        className="rounded-full bg-[var(--color-page)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[var(--color-text)]"
                      >
                        {criterionChip(l)}
                      </span>
                    ))}
                  </div>
                  <p className="text-sm font-semibold">{r.summary}</p>
                  <p className="text-xs text-[var(--color-muted)]">
                    ₱{r.metrics.totalFare.toFixed(2)} ·{" "}
                    {formatTime(r.metrics.totalTimeSec)} ·{" "}
                    {r.metrics.transfers} transfer
                    {r.metrics.transfers === 1 ? "" : "s"} · walk{" "}
                    {r.metrics.walkM} m
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {selected && (
        <section
          className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
          aria-label="Itinerary steps"
        >
          <h2 className="text-lg font-bold">Steps</h2>
          <ol className="mt-3 flex flex-col gap-3">
            {selected.legs.map((leg, i) => (
              <li
                key={`${leg.fromStopId}-${leg.toStopId}-${i}`}
                className="flex flex-col gap-1 rounded-xl bg-[var(--color-page)] px-3 py-2 text-sm"
              >
                <p className="font-semibold">
                  {leg.kind === "ride"
                    ? `Ride ${leg.routeCode ?? ""} ${leg.routeName ?? ""}`.trim()
                    : "Walk"}
                </p>
                <p className="text-[var(--color-muted)]">
                  {leg.fromStopName} → {leg.toStopName}
                </p>
                <p className="text-xs text-[var(--color-muted)]">
                  {Math.round(leg.distanceM)} m · {formatTime(leg.timeSec)}
                  {leg.kind === "ride" ? ` · ₱${leg.fare.toFixed(2)}` : ""}
                </p>
                {leg.verification_status && (
                  <span
                    className={`w-fit rounded-full px-2 py-0.5 text-[10px] font-bold ${verificationBadgeClass(leg.verification_status)}`}
                  >
                    {verificationLabel(leg.verification_status)}
                  </span>
                )}
              </li>
            ))}
          </ol>
          <p className="mt-4 text-sm font-semibold">
            Total ₱{selected.metrics.totalFare.toFixed(2)} ·{" "}
            {formatTime(selected.metrics.totalTimeSec)}
          </p>
        </section>
      )}
    </div>
  );
}
