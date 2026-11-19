import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Nav } from "@/components/Nav";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "mockai — AI Mock Interview Coach",
  description: "Spoken mock interviews grounded in your resume and the job description.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-900">
        <AuthProvider>
          <Nav />
          <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-8">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
