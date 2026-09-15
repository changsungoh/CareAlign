import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "CareAlign",
  description: "Aligning care instructions and verifying patient understanding.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
