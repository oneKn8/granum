import Link from "next/link";

export default function NotFound() {
  return (
    <main id="main" className="mx-auto flex min-h-dvh max-w-screen-md flex-col justify-center px-6 py-16">
      <p className="font-mono text-xs uppercase tracking-[0.16em] text-ink-subtle">404</p>
      <h1 className="mt-4 font-display text-2xl text-ink fraunces-head">
        Nothing grows on this plate.
      </h1>
      <p className="mt-4 max-w-prose font-body text-base text-ink-muted">
        The page you asked for does not exist. The cells live on the home page.
      </p>
      <Link
        href="/"
        className="mt-6 w-fit border-b border-primary pb-px font-mono text-xs text-primary-strong transition-colors hover:text-ink"
      >
        <span aria-hidden>←</span> back to home
      </Link>
    </main>
  );
}
