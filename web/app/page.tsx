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
          <div className="mx-auto grid max-w-screen-2xl grid-cols-12 gap-x-6 gap-y-10 px-6 py-16 lg:py-24">
            <Reveal className="col-span-12 self-center lg:col-span-6">
              <p className="mb-6 font-mono text-xs uppercase tracking-[0.16em] text-seed-ink">
                Google Cloud Rapid Agent · Arize Phoenix · 2026
              </p>
              <h1 className="font-display text-ink">
                A denied appeal that gets better every time it loses.
              </h1>
              <p className="mt-7 max-w-prose font-body text-base text-ink-muted lg:text-lg">
                When a health plan denies care your doctor says you need, an appeal overturns it about 83% of
                the time. Almost nobody files one. Each letter takes a physician roughly 12 hours to write, so
                most denials just stand.
              </p>
              <p className="mt-4 max-w-prose font-body text-base text-ink-muted lg:text-lg">
                Granum writes those appeals the way a body fights infection. For every payer and diagnosis it
                keeps a small population of strategies. A denial comes in, the strategies draft competing
                letters, a judge scores them against real overturned cases, and the best one is sent. Weak
                strategies die. Strong ones branch and keep improving.
              </p>
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

            <Reveal delay={0.12} className="col-span-12 lg:col-span-6 lg:-ml-10">
              <LineageTree
                strategies={aetna.strategies}
                caption={`${cellLabelFromMeta(aetna.meta)}, ${generations} generations`}
                height={540}
              />
              <p className="mt-3 font-body text-sm text-ink-muted">
                One strategy starts naive at <span className="font-mono text-ink">0.40</span> and climbs to a{" "}
                <span className="font-mono text-champion-ink">0.98</span> champion across ten generations. The
                strategies that died stay on the page, struck out, as a record of what did not work.
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
                  Every payer-and-diagnosis pairing is its own cell with a small population of B-cell
                  strategies. When a denial arrives, the survivors generate candidate appeals and an
                  LLM-as-judge scores them against a gold set of appeals that really were overturned. The
                  winner is submitted. The losing strategies are deleted from the Phoenix prompt registry for
                  good. No revert, no archive, no keeping them around just in case.
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
