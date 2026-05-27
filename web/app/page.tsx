import Link from "next/link";
import { LineageTree } from "@/components/LineageTree";
import { CellSelector } from "@/components/CellSelector";
import { getCellPayload } from "@/lib/api";

export default async function LandingPage() {
  const aetna = await getCellPayload("aetna_cardiac");

  return (
    <div className="min-h-dvh">
      {/* Top bar — static, minimal */}
      <header className="border-b border-stroke-1">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between gap-4 px-6 py-4">
          <Link href="/" className="flex items-baseline gap-3 font-serif text-fg-0">
            <span className="text-lg leading-none">Granum</span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-fg-2">
              an immune system for medical appeals
            </span>
          </Link>
          <nav aria-label="Primary" className="font-mono text-xs text-fg-1">
            <Link href="/cell/aetna_cardiac" className="hover:text-fg-0">
              explore cells →
            </Link>
          </nav>
        </div>
      </header>

      <main id="main">
        {/* Hero — asymmetric, serif headline left, tree right */}
        <section className="border-b border-stroke-1">
          <div className="mx-auto grid max-w-screen-2xl grid-cols-12 gap-x-6 px-6 py-16 lg:py-24">
            <div className="col-span-12 lg:col-span-6">
              <p className="mb-6 font-mono text-xs uppercase tracking-widest text-fg-2">
                Google Cloud Rapid Agent · Arize Phoenix track · 2026
              </p>
              <h1 className="font-serif text-3xl text-fg-0 lg:text-[64px] lg:leading-[68px]">
                Strategies that lose are{" "}
                <span className="text-apoptosis">permanently</span> deleted.
              </h1>
              <p className="mt-6 max-w-prose font-serif text-base text-fg-1 lg:text-[20px] lg:leading-[30px]">
                When your insurance denies medically necessary care, 83% of physician
                appeals succeed — but only 10% are ever filed. Writing one costs 12 hours
                of physician time. The math kills the appeal before it&rsquo;s written.
              </p>
              <p className="mt-4 max-w-prose font-serif text-base text-fg-1 lg:text-[20px] lg:leading-[30px]">
                Granum is an agent that drafts those appeals. It maintains an evolving
                population of strategies per (payer × diagnosis) — surviving lineages
                branch and mutate; losing ones undergo apoptosis. The lineage is the
                system of record.
              </p>
              <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-3 font-mono text-xs text-fg-2">
                <Link
                  href="/cell/aetna_cardiac"
                  className="border-b border-survivor pb-px text-survivor hover:text-fg-0"
                >
                  open the aetna · cardiac cell →
                </Link>
                <a
                  href="https://github.com/"
                  className="text-fg-1 hover:text-fg-0"
                  rel="noreferrer noopener"
                  target="_blank"
                >
                  source on github →
                </a>
              </div>
            </div>

            <div className="col-span-12 mt-10 lg:col-span-6 lg:mt-0 lg:-ml-12">
              <LineageTree
                strategies={aetna.strategies}
                caption="Aetna · Cardiac — 8 generations, 6 apoptosed"
                height={520}
              />
            </div>
          </div>
        </section>

        {/* Mechanism strip — single editorial column, no 3-card grid */}
        <section className="border-b border-stroke-1">
          <div className="mx-auto grid max-w-screen-2xl grid-cols-12 gap-x-6 px-6 py-16">
            <div className="col-span-12 lg:col-span-3">
              <p className="font-mono text-xs uppercase tracking-widest text-fg-2">
                mechanism
              </p>
            </div>
            <div className="col-span-12 lg:col-span-9 lg:col-start-4">
              <h2 className="font-serif text-xl text-fg-0 lg:text-2xl">
                Affinity maturation, applied to prompts.
              </h2>
              <p className="mt-4 max-w-prose font-serif text-base text-fg-1 lg:text-lg">
                Each (payer × diagnosis) cell holds a small population of B-cell appeal
                strategies. A new denial arrives; surviving strategies generate candidate
                appeals; an LLM-as-judge scores them against a gold dataset of prior
                overturned appeals. The winning candidate is submitted. The losing
                strategies&rsquo; prompt versions are deleted from the Phoenix registry —
                no revert, no archive, no &ldquo;keep around in case.&rdquo;
              </p>
              <dl className="mt-10 grid grid-cols-1 gap-x-8 gap-y-6 border-t border-stroke-1 pt-8 sm:grid-cols-3">
                <div>
                  <dt className="font-mono text-[10px] uppercase tracking-widest text-fg-2">
                    aetna · cardiac · baseline
                  </dt>
                  <dd className="mt-2 font-serif text-2xl text-fg-tomb">41%</dd>
                  <dd className="font-mono text-xs text-fg-2">overturn rate, gen 0</dd>
                </div>
                <div>
                  <dt className="font-mono text-[10px] uppercase tracking-widest text-fg-2">
                    after 8 generations
                  </dt>
                  <dd className="mt-2 font-serif text-2xl text-champion">79%</dd>
                  <dd className="font-mono text-xs text-fg-2">overturn rate, champion</dd>
                </div>
                <div>
                  <dt className="font-mono text-[10px] uppercase tracking-widest text-fg-2">
                    strategies apoptosed
                  </dt>
                  <dd className="mt-2 font-serif text-2xl text-apoptosis">6</dd>
                  <dd className="font-mono text-xs text-fg-2">
                    permanent removal from registry
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </section>

        {/* Explore cells */}
        <section>
          <div className="mx-auto max-w-screen-2xl px-6 py-16">
            <div className="mb-6 flex items-baseline justify-between">
              <h2 className="font-serif text-xl text-fg-0">Explore the cells.</h2>
              <p className="font-mono text-xs text-fg-2">5 (payer × diagnosis) cells</p>
            </div>
            <CellSelector />
          </div>
        </section>
      </main>

      <footer className="border-t border-stroke-1">
        <div className="mx-auto max-w-screen-2xl px-6 py-6 font-mono text-[11px] text-fg-2">
          Apache-2.0 · built on Google ADK + Gemini + Arize Phoenix · synthetic data only,
          no PHI
        </div>
      </footer>
    </div>
  );
}
