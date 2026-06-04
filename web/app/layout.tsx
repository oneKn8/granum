import type { Metadata, Viewport } from "next";
import { Fraunces, Hanken_Grotesk, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

// "Germinal" type stack — organism / human / instrument.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["opsz", "SOFT", "WONK"],
  display: "swap",
});

const hanken = Hanken_Grotesk({
  variable: "--font-hanken",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

// Canonical / Open Graph base URL. Override at deploy with NEXT_PUBLIC_SITE_URL.
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://granum.app";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Granum — an immune system for medical appeals",
    template: "%s · Granum",
  },
  description:
    "Granum evolves prior-authorization appeals like B-cells in a germinal center. A naive seed strategy matures across generations; surviving lineages branch, losing ones undergo apoptosis. Watch a denied appeal climb from 0.40 to 0.98.",
  applicationName: "Granum",
  authors: [{ name: "Granum" }],
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "Granum",
    title: "Granum — an immune system for medical appeals",
    description:
      "An evolutionary appeal-writer for denied medical care. A seed strategy matures into a champion across ten generations; the lineage is the system of record.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Granum — an immune system for medical appeals",
    description:
      "Affinity maturation for denied medical care. Built on Google ADK + Gemini + Arize Phoenix.",
  },
  alternates: {
    canonical: SITE_URL,
  },
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: [{ url: "/favicon.svg", type: "image/svg+xml" }],
  },
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#f7f3ea",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${hanken.variable} ${plexMono.variable}`}
    >
      <body>
        <a
          href="#main"
          className="sr-only focus-visible:not-sr-only focus-visible:fixed focus-visible:top-3 focus-visible:left-3 focus-visible:z-50 focus-visible:border focus-visible:border-border-strong focus-visible:bg-surface focus-visible:px-3 focus-visible:py-2 focus-visible:text-ink"
        >
          Skip to main content
        </a>
        {children}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "Granum",
              applicationCategory: "HealthApplication",
              operatingSystem: "Web",
              description:
                "Evolutionary appeal-writer for denied medical care. Strategies undergo affinity maturation against payer denial patterns.",
              url: SITE_URL,
              offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
            }),
          }}
        />
      </body>
    </html>
  );
}
