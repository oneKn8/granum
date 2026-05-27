import Link from "next/link";

export default function NotFound() {
  return (
    <main id="main" className="mx-auto flex min-h-dvh max-w-screen-md flex-col justify-center px-6 py-16">
      <p className="font-mono text-xs uppercase tracking-widest text-fg-2">404</p>
      <h1 className="mt-4 font-serif text-2xl text-fg-0">
        That cell hasn&rsquo;t been seeded yet.
      </h1>
      <p className="mt-4 font-serif text-base text-fg-1">
        Granum holds five (payer × diagnosis) cells. Pick one from the list and explore
        its lineage.
      </p>
      <Link
        href="/"
        className="mt-6 border-b border-survivor pb-px font-mono text-xs text-survivor hover:text-fg-0"
      >
        ← back to home
      </Link>
    </main>
  );
}
