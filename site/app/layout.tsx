import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import AnalyticsConsent from "@/components/AnalyticsConsent";
import PostHogProvider from "@/components/PostHogProvider";
import StructuredData from "@/components/StructuredData";
import { rootMetadata } from "@/lib/metadata";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata = rootMetadata;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <StructuredData />
        <PostHogProvider>
          {children}
          <AnalyticsConsent />
        </PostHogProvider>
      </body>
    </html>
  );
}
