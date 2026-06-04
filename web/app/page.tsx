import Link from "next/link";
import { LineageTree } from "@/components/LineageTree";
import { CellSelector } from "@/components/CellSelector";
import { LivePoll } from "@/components/LivePoll";
import { Reveal } from "@/components/Reveal";
import { getCellPayload, listCellMetas } from "@/lib/api";
import { cellLabelFromMeta } from "@/lib/mock-data";

export default async function LandingPage() {
  const [aetna, cellMetas] = await Promise.all([
    getCellPayload("aetna_cardiac"),
    listCellMetas(),
  ]);
  const navItems = cellMetas.map((m) => ({ id: m.id, label: cellLabelFromMeta(m) }));
  const { baselineOverturn, currentOverturn, generations, apoptosisTotal } = aetna.meta;
  const pct = (v: number) => `${Math.round(v * 100)}%`;

  return (
    <div className="min-h-dvh">
      {/* Top bar */}
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between gap-4 px-6 py-4">
          <Link href="/" className="flex items-baseline gap-3 text-ink">
            <span className="font-display text-lg leading-none fraunces-head">Granum</span>
            <span className="hidden font-mono text-[10px] uppercase tracking-[0.16em] text-ink-subtle sm:inline">
              an immune system for medical appeals
            </span>
          </Link>
          <nav aria-label="Primary" className="font-mono text-xs text-ink-muted">
            <Link href="/cell/aetna_cardiac" className="hover:text-ink">
              explore cells <span aria-hidden>→</span>
            </Link>
          </nav>
        </div>
      </header>

      <main id="main">
        <LivePoll />

        {/* Hero */}
        <section className="border-b border-border">
          <div className="mx-auto grid max-w-screen-2xl grid-cols-12 items-center gap-x-10 gap-y-12 px-6 py-16 lg:py-24">
            <Reveal className="col-span-12 lg:col-span-5">
              <p className="mb-6 font-mono text-xs uppercase tracking-[0.16em] text-seed-ink">
                Google Cloud Rapid Agent · Arize Phoenix · 2026
              </p>
              <h1 className="font-display text-ink">
                A denied appeal that gets better every time it loses.
              </h1>
              <p className="mt-6 font-body text-base text-ink-muted lg:text-lg">
                Granum evolves insurance-appeal letters like an immune system. A naive draft matures into a
                champion that wins.
              </p>
              <dl className="mt-8 flex flex-wrap gap-x-9 gap-y-5">
                {[
                  ["83%", "overturned when filed"],
                  ["10%", "ever appealed"],
                  ["12h", "to write by hand"],
                ].map(([n, label]) => (
                  <div key={label}>
                    <dt className="font-display text-2xl font-light leading-none text-ink">{n}</dt>
                    <dd className="mt-1.5 font-mono text-[11px] text-ink-muted">{label}</dd>
                  </div>
                ))}
              </dl>
              <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-3 font-mono text-xs">
                <Link
                  href="/cell/aetna_cardiac"
                  className="border-b border-primary pb-px text-primary-strong transition-colors hover:text-ink"
                >
                  open the Aetna cardiac cell <span aria-hidden>→</span>
                </Link>
                <a
                  href="https://github.com/oneKn8/granum"
                  className="text-ink-muted transition-colors hover:text-ink"
                  rel="noreferrer noopener"
                  target="_blank"
                >
                  source on GitHub <span aria-hidden>→</span>
                </a>
              </div>
            </Reveal>

            <Reveal delay={0.12} className="col-span-12 lg:col-span-7">
              <LineageTree
                strategies={aetna.strategies}
                caption={`${cellLabelFromMeta(aetna.meta)}, ${generations} generations`}
                height={520}
              />
              <p className="mt-3 font-body text-sm text-ink-muted">
                One strategy starts at <span className="font-mono text-ink">0.40</span> and climbs to a{" "}
                <span className="font-mono text-champion-ink">0.98</span> champion. The losers stay on the
                page, struck out.
              </p>
            </Reveal>
          </div>
        </section>

        {/* Mechanism */}
        <section className="border-b border-border">
          <div className="mx-auto grid max-w-screen-2xl grid-cols-12 gap-x-6 gap-y-8 px-6 py-16 lg:py-20">
            <Reveal className="col-span-12 lg:col-span-3">
              <p className="font-mono text-xs uppercase tracking-[0.16em] text-ink-subtle">how it works</p>
            </Reveal>
            <div className="col-span-12 lg:col-span-9 lg:col-start-4">
              <Reveal>
                <h2 className="font-display text-xl text-ink lg:text-2xl fraunces-head">
                  It treats each appeal strategy like a living cell.
                </h2>
                <p className="mt-5 max-w-prose font-body text-base text-ink-muted lg:text-lg">
                  Every payer and diagnosis gets its own population. On each denial the strategies draft
                  competing letters, a judge scores them against real overturned cases, and the losers are
                  deleted from the registry for good. Winners branch.
                </p>
              </Reveal>
              <Reveal delay={0.08}>
                <dl className="mt-10 grid grid-cols-1 gap-x-8 gap-y-7 border-t border-border pt-8 sm:grid-cols-3">
                  <div>
                    <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-subtle">
                      Aetna · cardiac · seed
                    </dt>
                    <dd className="mt-2 font-display text-2xl font-light text-ink-subtle">
                      {pct(baselineOverturn)}
                    </dd>
                    <dd className="font-mono text-xs text-ink-subtle">appeal fitness, naive gen 0</dd>
                  </div>
                  <div>
                    <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-subtle">
                      after {generations} generations
                    </dt>
                    <dd className="mt-2 font-display text-2xl font-light text-champion-ink">
                      {pct(currentOverturn)}
                    </dd>
                    <dd className="font-mono text-xs text-ink-subtle">appeal fitness, champion</dd>
                  </div>
                  <div>
                    <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-subtle">
                      strategies apoptosed
                    </dt>
                    <dd className="mt-2 font-display text-2xl font-light text-removed">{apoptosisTotal}</dd>
                    <dd className="font-mono text-xs text-ink-subtle">deleted from the registry, kept on record</dd>
                  </div>
                </dl>
              </Reveal>
            </div>
          </div>
        </section>

        {/* Explore */}
        <section>
          <div className="mx-auto max-w-screen-2xl px-6 py-16">
            <Reveal className="mb-6 flex items-baseline justify-between gap-4">
              <h2 className="font-display text-xl text-ink fraunces-head">Look inside a cell.</h2>
              <p className="font-mono text-xs text-ink-subtle">
                {navItems.length} payer{navItems.length === 1 ? "" : "s"} and diagnoses
              </p>
            </Reveal>
            <Reveal delay={0.06}>
              <CellSelector items={navItems} />
            </Reveal>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto max-w-screen-2xl px-6 py-6 font-mono text-[11px] text-ink-subtle">
          Apache-2.0 · built on Google ADK, Gemini, and Arize Phoenix · synthetic data only, no PHI
        </div>
      </footer>
    </div>
  );
}
