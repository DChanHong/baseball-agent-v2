"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { Provider as JotaiProvider } from "jotai";
import { useState, type ReactNode } from "react";
import { ThemeProvider } from "styled-components";
import { createQueryClient } from "@/shared/lib/query/create-query-client";
import { GlobalStyle } from "@/shared/styles/global-style";
import { theme } from "@/shared/styles/theme";
import { GlobalModal } from "@/widgets/global-modal";

type AppProvidersProps = {
  children: ReactNode;
};

export function AppProviders({ children }: AppProvidersProps) {
  const [queryClient] = useState(() => createQueryClient());

  return (
    <JotaiProvider>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <GlobalStyle />
          {children}
          <div id="modal-portal-root" />
          <GlobalModal />
        </ThemeProvider>
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </JotaiProvider>
  );
}
