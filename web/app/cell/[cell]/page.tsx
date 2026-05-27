import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CellDashboard } from "@/components/CellDashboard";
import { CellSelector } from "@/components/CellSelector";
import {
  ALL_CELLS,
  CELL_LABEL,
  CELL_LIST,
  getCell,
  getCoEvolution,
} from "@/lib/mock-data";
import type { CellId } from "@/lib/types";

interface CellPageProps {
  params: Promise<{ cell: string }>;
}

export function generateStaticParams() {
  return CELL_LIST.map((id) => ({ cell: id }));
}

function isCellId(id: string): id is CellId {
  return id in ALL_CELLS;
}

export async function generateMetadata({ params }: CellPageProps): Promise<Metadata> {
  const { cell } = await params;
  if (!isCellId(cell)) return { title: "Cell not found" };
  const meta = getCell(cell).meta;
  const title = `${meta.payer} · ${meta.diagnosis}`;
  const description = `Granum lineage for ${title}. Baseline overturn ${(meta.baselineOverturn * 100).toFixed(0)}% → champion ${(meta.currentOverturn * 100).toFixed(0)}% across ${meta.generations} generations.`;
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

  const payload = getCell(cell);
  const coEvolution = getCoEvolution(cell);
  const meta = payload.meta;

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
          <CellSelector current={cell} />
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
              <span className="text-fg-tomb">{meta.apoptosisTotal}</span>
            </p>
          </div>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-fg-2">
              overturn lift
            </p>
            <p className="mt-1 font-mono text-base text-fg-0">
              <span className="text-fg-tomb">
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
