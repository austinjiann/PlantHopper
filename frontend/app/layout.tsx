import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Plant Hopper Dashboard",
  description: "Monitor and manage every plant in your robotic care fleet."
};

export default function RootLayout({
  children
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="bg-leaves" aria-hidden="true" />
        <Sidebar />
        <div className="mini-sidebar-offset">{children}</div>
      </body>
    </html>
  );
}
