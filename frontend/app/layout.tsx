import type { Metadata } from "next";
import { DM_Sans, Outfit } from "next/font/google";
import { Sidebar } from "@/components/Sidebar";
import "./globals.css";

const display = Outfit({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const body = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "OptiChain",
  description:
    "Supply chain intelligence and optimization — forecast, optimize, simulate.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${body.variable} font-sans antialiased`}>
        <div className="oc-shell flex min-h-screen text-ink">
          <Sidebar />
          <main className="relative flex-1 overflow-y-auto bg-slate-50">
            <div className="relative z-10 min-h-screen">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
