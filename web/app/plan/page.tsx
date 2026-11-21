import Link from "next/link";
import PlanForm from "@/components/plan/PlanForm";

export const metadata = {
  title: "Plan — BIYAHERO",
  description: "Multi-criteria public transport recommendations for Naga City.",
};

export default function PlanPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-6 px-4 py-8">
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
        <span className="font-medium">Plan</span>
        <Link
          href="/map"
          className="ml-auto font-semibold text-[var(--color-muted)] underline-offset-2 hover:underline"
        >
          Map
        </Link>
      </nav>
      <PlanForm />
    </main>
  );
}
