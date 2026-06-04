import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CellDashboard } from "@/components/CellDashboard";
import { CellSelector } from "@/components/CellSelector";
import { LivePoll } from "@/components/LivePoll";
import { ApiError, getCellPayload, getCoEvolution, listCellMetas } from "@/lib/api";
import { ALL_CELLS, CELL_LABEL, cellLabelFromMeta, titleCase } from "@/lib/mock-data";
import type { CellId, CellMeta, CellPayload, CoEvolutionState } from "@/lib/types";

interface CellPageProps {
  params: Promise<{ cell: string }>;
}

export async function generateStaticParams() {
  // Data-driven: only pre-render cells the live API actually serves.
  const metas = await listCellMetas();
  return metas.map((m) => ({ cell: m.id }));
}

function isCellId(id: string): id is CellId {
  return id in ALL_CELLS;
}

export async function generateMetadata({ params }: CellPageProps): Promise<Metadata> {
  const { cell } = await params;
  if (!isCellId(cell)) return { title: "Cell not found" };
  let meta: CellMeta;
  try {
    ({ meta } = await getCellPayload(cell));
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return { title: "Cell not found" };
    throw err;
  }
  const title = `${titleCase(meta.payer)} · ${titleCase(meta.diagnosis)}`;
  const description = `Granum lineage for ${title}. A seed strategy matures from ${(meta.baselineOverturn * 100).toFixed(0)}% to ${(meta.currentOverturn * 100).toFixed(0)}% appeal fitness across ${meta.generations} generations.`;
  const path = `/cell/${cell}`;
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: { type: "website", url: path, title, description, siteName: "Granum" },
    twitter: { card: "summary_large_image", title, description },
  };
}

export default async function CellPage({ params }: CellPageProps) {
  const { cell } = await params;
  if (!isCellId(cell)) notFound();

  let payload: CellPayload;
  let coEvolution: CoEvolutionState;
  let cellMetas: CellMeta[];
  try {
    [payload, coEvolution, cellMetas] = await Promise.all([
      getCellPayload(cell),
      getCoEvolution(cell),
      listCellMetas(),
    ]);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }
  const meta = payload.meta;
  const navItems = cellMetas.map((m) => ({ id: m.id, label: cellLabelFromMeta(m) }));
  const lift = meta.currentOverturn - meta.baselineOverturn;

  const stat = (label: string, value: React.ReactNode) => (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-subtle">{label}</p>
      <p className="mt-1.5 font-body text-base text-ink">{value}</p>
    </div>
  );

  return (
    <div className="min-h-dvh">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center justify-between gap-3 px-6 py-3">
          <Link href="/" className="flex items-baseline gap-3 text-ink">
            <span className="font-display text-lg leading-none fraunces-head">Granum</span>
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-subtle">
              {CELL_LABEL[cell]}
            </span>
          </Link>
          <CellSelector current={cell} items={navItems} />
        </div>
      </header>

      <main id="main" className="mx-auto max-w-screen-2xl px-6 py-8">
        <h1 className="sr-only">
          {titleCase(meta.payer)}, {titleCase(meta.diagnosis)} lineage
        </h1>

        <section
          className="mb-8 grid grid-cols-2 gap-x-6 gap-y-5 border border-border bg-surface/70 p-6 lg:grid-cols-5"
          aria-label="Cell summary"
        >
          {stat("payer", titleCase(meta.payer))}
          {stat("diagnosis", titleCase(meta.diagnosis))}
          {stat("generations", <span className="font-mono">{meta.generations}</span>)}
          {stat(
            "alive · apoptosed",
            <span className="font-mono">
              <span className="text-alive">{meta.populationSize}</span>
              <span className="text-ink-subtle"> · </span>
              <span className="text-dead-ink">{meta.apoptosisTotal}</span>
            </span>,
          )}
          {stat(
            "appeal fitness",
            <span className="font-mono">
              <span className="text-ink-subtle">{(meta.baselineOverturn * 100).toFixed(0)}%</span>{" "}
              <span aria-hidden>→</span>{" "}
              <span className="text-champion-ink">{(meta.currentOverturn * 100).toFixed(0)}%</span>{" "}
              <span className="text-ink-subtle">(+{(lift * 100).toFixed(0)}pp)</span>
            </span>,
          )}
        </section>

        <LivePoll />
        <CellDashboard payload={payload} coEvolution={coEvolution} />
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto max-w-screen-2xl px-6 py-6 font-mono text-[11px] text-ink-subtle">
          Apache-2.0 · synthetic data only, no PHI
        </div>
      </footer>
    </div>
  );
}
