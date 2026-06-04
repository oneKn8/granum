"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

interface LivePollProps {
  /** Poll interval in milliseconds. */
  intervalMs?: number;
}

// Only poll when pointed at the real API — mock data never changes, so there is
// nothing to refresh in local/mock mode.
const REAL_API =
  process.env.NEXT_PUBLIC_USE_REAL_API === "true" ||
  process.env.NEXT_PUBLIC_USE_REAL_API === "1";

/**
 * Re-fetches the page's server data on an interval via router.refresh(), so the
 * deployed site reflects the live API as a germinal run progresses — the lineage
 * tree and fitness curve grow on their own, no client-side animation. Renders
 * nothing. Pauses while the tab is hidden to avoid pointless background fetches.
 */
export function LivePoll({ intervalMs = 4000 }: LivePollProps) {
  const router = useRouter();

  useEffect(() => {
    if (!REAL_API || !intervalMs) return;
    let timer: ReturnType<typeof setInterval> | null = null;
    const start = () => {
      if (!timer) timer = setInterval(() => router.refresh(), intervalMs);
    };
    const stop = () => {
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    };
    const onVisibility = () =>
      document.visibilityState === "visible" ? start() : stop();

    if (document.visibilityState === "visible") start();
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [router, intervalMs]);

  return null;
}
