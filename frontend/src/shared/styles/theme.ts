export const theme = {
  color: {
    background: "#f7f8f3",
    foreground: "#17201c",
    muted: "#647067",
    panel: "#ffffff",
    panelAlt: "#eef3ef",
    border: "#d9e1dc",
    primary: "#136f4a",
    primaryHover: "#0d593b",
    accent: "#d94635",
    warning: "#b7791f",
    info: "#1d5f91",
  },
  radius: {
    sm: "6px",
    md: "8px",
  },
  shadow: {
    panel: "0 18px 50px rgba(18, 32, 25, 0.08)",
  },
  layout: {
    maxWidth: "1180px",
  },
} as const;

export type AppTheme = typeof theme;
