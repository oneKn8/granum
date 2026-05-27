import type { Metadata, Viewport } from "next";
import { IBM_Plex_Serif, IBM_Plex_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const plexSerif = IBM_Plex_Serif({
  variable: "--font-plex-serif",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});

const SITE_URL = "https://granum.app";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Granum — An immune system for medical appeals",
    template: "%s · Granum",
  },
  description:
    "Granum drafts prior-authorization appeals for denied patients. Strategies evolve like B-cells: surviving lineages branch, losing ones are permanently deleted.",
  applicationName: "Granum",
  authors: [{ name: "Granum" }],
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "Granum",
    title: "Granum — An immune system for medical appeals",
    description:
      "Evolutionary appeal-writer for denied medical care. Lineages branch on wins; losing strategies undergo apoptosis.",
    images: [
      {
        url: "/og.png",
        width: 1200,
        height: 630,
        alt: "Granum lineage tree — surviving strategies branch, tombstoned strategies remain greyed.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Granum — An immune system for medical appeals",
    description:
      "Evolutionary appeal-writer for denied medical care. Built on Google ADK + Arize Phoenix.",
    images: ["/og.png"],
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
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#1a1623",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${plexSerif.variable} ${plexSans.variable} ${jetbrains.variable}`}>
      <body>
        <a
          href="#main"
          className="sr-only focus-visible:not-sr-only focus-visible:fixed focus-visible:top-3 focus-visible:left-3 focus-visible:z-50 focus-visible:rounded-none focus-visible:bg-bg-2 focus-visible:px-3 focus-visible:py-2 focus-visible:text-fg-0"
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
