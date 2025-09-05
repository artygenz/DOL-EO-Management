import { createTheme } from "@mui/material/styles";

const fonts = [
  // Inter if present; otherwise platform system stacks (no FOUT)
  "Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto",
  "Helvetica Neue", "Arial", "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji",
  "Segoe UI Symbol", "sans-serif"
].join(",");

const baseComponents = {
  MuiCssBaseline: {
    styleOverrides: {
      body: {
        letterSpacing: 0.1,
        textRendering: "optimizeLegibility",
      }
    }
  },
  MuiAppBar: {
    styleOverrides: {
      root: { backdropFilter: "saturate(180%) blur(8px)" },
      colorInherit: { backgroundColor: "transparent" }
    }
  },
  MuiContainer: {
    defaultProps: { maxWidth: "lg" }
  },
  MuiCard: {
    defaultProps: { elevation: 0 },
    styleOverrides: {
      root: {
        borderRadius: 16,
        border: "1px solid",
        borderColor: "var(--card-border, #e5e7eb)",
        transition: "transform 160ms ease, box-shadow 160ms ease",
        willChange: "transform",
      }
    }
  },
  MuiButton: {
    defaultProps: { variant: "contained", size: "medium" },
    styleOverrides: {
      root: {
        textTransform: "none",
        borderRadius: 12,
        paddingInline: 14,
      }
    }
  },
  MuiChip: {
    defaultProps: { size: "small" },
    styleOverrides: { root: { borderRadius: 10 } }
  },
  MuiTextField: {
    defaultProps: { size: "small" }
  },
  MuiTooltip: {
    defaultProps: { arrow: true }
  },
  // DataGrid polish (header bg, hover, borders)
  MuiDataGrid: {
    styleOverrides: {
      root: {
        border: "1px solid #e5e7eb",
        borderRadius: 12,
      },
      columnHeaders: {
        backgroundColor: "rgba(0,0,0,0.03)",
        borderBottom: "1px solid #e5e7eb",
      },
      row: {
        "&:hover": { backgroundColor: "rgba(0,0,0,0.02)" }
      }
    }
  }
};

export const themeLight = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#0ea5a4" },           // teal
    secondary: { main: "#14532d" },         // deep green
    background: { default: "#f7f8fb", paper: "#ffffff" },
    divider: "#e5e7eb",
  },
  typography: {
    fontFamily: fonts,
    h5: { fontWeight: 700, letterSpacing: 0.2 },
    h6: { fontWeight: 700 },
    body1: { fontSize: 14.5 },
    body2: { fontSize: 13.5 }
  },
  shape: { borderRadius: 12 },
  shadows: [
    "none",
    "0 2px 6px rgba(0,0,0,0.06)",
    ...Array(23).fill("0 8px 24px rgba(0,0,0,0.08)")
  ],
  components: {
    ...baseComponents,
  }
});

export const themeDark = createTheme({
  palette: {
    mode: "dark",
    primary: { main: "#22d3ee" },           // cyan
    secondary: { main: "#86efac" },
    background: { default: "#0b0f17", paper: "#111827" },
    divider: "rgba(255,255,255,0.12)",
  },
  typography: {
    fontFamily: fonts,
    h5: { fontWeight: 700, letterSpacing: 0.2 },
    h6: { fontWeight: 700 },
    body1: { fontSize: 14.5 },
    body2: { fontSize: 13.5 }
  },
  shape: { borderRadius: 12 },
  shadows: [
    "none",
    "0 2px 6px rgba(0,0,0,0.35)",
    ...Array(23).fill("0 12px 28px rgba(0,0,0,0.45)")
  ],
  components: {
    ...baseComponents,
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderColor: "rgba(255,255,255,0.08)",
          "--card-border": "rgba(255,255,255,0.08)"
        }
      }
    },
    MuiDataGrid: {
      styleOverrides: {
        root: {
          borderColor: "rgba(255,255,255,0.12)"
        },
        columnHeaders: {
          backgroundColor: "rgba(255,255,255,0.04)",
          borderBottom: "1px solid rgba(255,255,255,0.12)"
        },
        row: {
          "&:hover": { backgroundColor: "rgba(255,255,255,0.04)" }
        }
      }
    }
  }
});
