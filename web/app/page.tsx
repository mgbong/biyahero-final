import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-8 px-4 py-10">
      <header className="flex flex-col gap-3">
        <p className="text-sm font-semibold uppercase tracking-wide text-[var(--color-muted)]">
          Naga City · Camarines Sur
        </p>
        <h1 className="text-4xl font-bold tracking-tight text-[var(--color-text)]">
          BIYAHERO
        </h1>
        <p className="max-w-xl text-base leading-relaxed text-[var(--color-muted)]">
          Commuter route recommendations for jeepneys, tricycles, and buses.
        </p>
        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            href="/map"
            className="inline-flex items-center rounded-full bg-[var(--color-accent)] px-5 py-2.5 text-sm font-bold text-white hover:brightness-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
          >
            Open map
          </Link>
        </div>
      </header>

      <section
        className="rounded-2xl bg-[var(--color-surface)] p-5 shadow-[rgba(0,0,0,0.01)_0_2px_2px_0]"
        aria-labelledby="phase-title"
      >
        <h2 id="phase-title" className="text-lg font-semibold">
          Build progress
        </h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-relaxed text-[var(--color-muted)]">
          <li>
            <strong className="text-[var(--color-text)]">Phase 1</strong> —
            schema, Naga seed, Supabase clients
          </li>
          <li>
            <strong className="text-[var(--color-text)]">Phase 2</strong> —
            Leaflet map with route polylines, stop markers, verification badges
          </li>
          <li>Phase 3 — multi-criteria route graph (next)</li>
        </ul>
      </section>
    </main>
  );
}
