"use client";

// Route-level error boundary: a transient API failure (cold start, network
// blip) lands here instead of Next's unstyled default screen. The page polls
// live data, so a retry usually recovers on the spot.
export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main id="main" className="mx-auto flex min-h-dvh max-w-screen-md flex-col justify-center px-6 py-16">
      <p className="font-mono text-xs uppercase tracking-[0.16em] text-ink-subtle">temporary fault</p>
      <h1 className="mt-4 font-display text-2xl text-ink fraunces-head">
        The culture is unreachable.
      </h1>
      <p className="mt-4 max-w-prose font-body text-base text-ink-muted">
        The lineage data did not load. This is usually a brief network fault; the run itself is safe.
      </p>
      {error.digest ? (
        <p className="mt-2 font-mono text-[11px] text-ink-subtle">ref {error.digest}</p>
      ) : null}
      <button
        type="button"
        onClick={reset}
        className="mt-6 w-fit border-b border-primary pb-px font-mono text-xs text-primary-strong transition-colors hover:text-ink"
      >
        try again <span aria-hidden>→</span>
      </button>
    </main>
  );
}
