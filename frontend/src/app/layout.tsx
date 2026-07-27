import type { Metadata } from "next";
import { AppProviders } from "./providers";
import { StyledComponentsRegistry } from "./styled-components-registry";
import "./globals.css";

export const metadata: Metadata = {
  title: "Baseball Agent",
  description: "KBO game, stadium, weather, ticketing, and seat recommendation agent.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>
        <StyledComponentsRegistry>
          <AppProviders>{children}</AppProviders>
        </StyledComponentsRegistry>
      </body>
    </html>
  );
}
