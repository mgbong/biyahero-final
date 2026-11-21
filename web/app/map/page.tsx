import Link from "next/link";
import TransitMap from "@/components/map/TransitMap";

export const metadata = {
  title: "Map — BIYAHERO",
  description: "Naga City transit routes and stops on an interactive map.",
};

export default function MapPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 px-4 py-8">
      <nav className="flex flex-wrap items-center gap-3 text-sm">
        <Link
          href="/"
          className="font-semibold text-[var(--color-accent)] underline-offset-2 hover:underline"
        >
          BIYAHERO
        </Link>
        <span className="text-[var(--color-muted)]" aria-hidden>
          /
        </span>
        <span className="font-medium text-[var(--color-text)]">Map</span>
      </nav>
      <TransitMap />
    </main>
  );
}
