import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CellDashboard } from "@/components/CellDashboard";
import { CellSelector } from "@/components/CellSelector";
import { LivePoll } from "@/components/LivePoll";
import { ApiError, getCellPayload, getCoEvolution, listCellMetas } from "@/lib/api";
import { ALL_CELLS, CELL_LABEL, cellLabelFromMeta } from "@/lib/mock-data";
import type { CellId, CellMeta, CellPayload, CoEvolutionState } from "@/lib/types";

interface CellPageProps {
  params: Promise<{ cell: string }>;
}

export async function generateStaticParams() {
  // Data-driven: only pre-render cells the live API actually serves, so a
  // real-API build doesn't try (and fail) to render unseeded cells.
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
    // Unseeded cell on the live API → minimal metadata; the page itself 404s.
    if (err instanceof ApiError && err.status === 404) return { title: "Cell not found" };
    throw err;
  }
  const title = `${meta.payer} · ${meta.diagnosis}`;
  const description = `Granum lineage for ${title}. Baseline appeal fitness ${(meta.baselineOverturn * 100).toFixed(0)}% → champion ${(meta.currentOverturn * 100).toFixed(0)}% across ${meta.generations} generations.`;
  const path = `/cell/${cell}`;
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      url: path,
      title,
      description,
      siteName: "Granum",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
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
    // A known cell id the live API hasn't seeded (404) → 404 page, not a 500.
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }
  const meta = payload.meta;
  const navItems = cellMetas.map((m) => ({ id: m.id, label: cellLabelFromMeta(m) }));

  const lift = meta.currentOverturn - meta.baselineOverturn;

  return (
    <div className="min-h-dvh">
      <header className="border-b border-stroke-1">
        <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center justify-between gap-3 px-6 py-3">
          <Link
            href="/"
            className="flex items-baseline gap-3 font-serif text-fg-0"
          >
            <span className="text-lg leading-none">Granum</span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-fg-2">
              {CELL_LABEL[cell]}
            </span>
          </Link>
          <CellSelector current={cell} items={navItems} />
        </div>
      </header>

      <main id="main" className="mx-auto max-w-screen-2xl px-6 py-8">
        <h1 className="sr-only">
          {meta.payer} · {meta.diagnosis} — lineage
        </h1>
        {/* Cell meta strip */}
        <section
          className="mb-8 grid grid-cols-2 gap-x-6 gap-y-4 border border-stroke-1 bg-bg-1 p-6 lg:grid-cols-5"
          aria-label="Cell summary"
        >
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-fg-2">
              payer
            </p>
            <p className="mt-1 font-serif text-base text-fg-0">{meta.payer}</p>
          </div>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-fg-2">
              diagnosis
            </p>
            <p className="mt-1 font-serif text-base text-fg-0">{meta.diagnosis}</p>
          </div>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-fg-2">
              generations
            </p>
            <p className="mt-1 font-mono text-base text-fg-0">{meta.generations}</p>
          </div>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-fg-2">
              alive · apoptosed
            </p>
            <p className="mt-1 font-mono text-base text-fg-0">
              <span className="text-survivor">{meta.populationSize}</span>
              <span className="text-fg-2"> · </span>
              <span className="text-fg-2">{meta.apoptosisTotal}</span>
            </p>
          </div>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-fg-2">
              appeal fitness
            </p>
            <p className="mt-1 font-mono text-base text-fg-0">
              <span className="text-fg-2">
                {(meta.baselineOverturn * 100).toFixed(0)}%
              </span>{" "}
              →{" "}
              <span className="text-champion">
                {(meta.currentOverturn * 100).toFixed(0)}%
              </span>{" "}
              <span className="text-fg-2">(+{(lift * 100).toFixed(0)}pp)</span>
            </p>
          </div>
        </section>

        <LivePoll />
        <CellDashboard payload={payload} coEvolution={coEvolution} />
      </main>

      <footer className="border-t border-stroke-1">
        <div className="mx-auto max-w-screen-2xl px-6 py-6 font-mono text-[11px] text-fg-2">
          Apache-2.0 · synthetic data only, no PHI
        </div>
      </footer>
    </div>
  );
}
