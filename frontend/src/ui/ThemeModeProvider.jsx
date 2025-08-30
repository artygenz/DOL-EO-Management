import React, { createContext, useContext, useState } from "react";
import { ThemeProvider } from "@mui/material/styles";
import { CssBaseline } from "@mui/material";
import { themeLight, themeDark } from "../theme";

const ThemeModeContext = createContext();

export function ThemeModeProvider({ children }) {
  const [mode, setMode] = useState("light");

  const toggle = () => setMode(mode === "light" ? "dark" : "light");

  return (
    <ThemeModeContext.Provider value={{ mode, toggle }}>
      <ThemeProvider theme={mode === "light" ? themeLight : themeDark}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeModeContext.Provider>
  );
}

export const useThemeMode = () => useContext(ThemeModeContext);
