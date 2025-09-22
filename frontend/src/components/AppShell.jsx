import React from "react";
import { AppBar, Toolbar, Typography, Button, IconButton, Tooltip, Container, Box } from "@mui/material";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useThemeMode } from "../ui/ThemeModeProvider";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import PageFade from "../ui/PageFade";
import Footer from "./Footer";

export default function AppShell({ children }) {
  const { isAuthenticated, loading, user, logout } = useAuth();
  const { pathname } = useLocation();
  const { mode, toggle } = useThemeMode();
  const isActive = (m) => pathname === m || pathname.startsWith(m);

  const handleLogout = () => {
    logout();
  };

  // Don't render until user data is fully loaded
  if (loading || !user) {
    return <div>Loading...</div>;
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="sticky" elevation={0} color="inherit" sx={{ borderBottom: "1px solid", borderColor: "divider" }}>
        <Toolbar sx={{ display: "flex", gap: 1.25, minHeight: 64 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexGrow: 1 }}>
            <Box
              component="img"
              src="/llila-logo.jpeg"
              alt="LLILA Logo"
              sx={{
                height: 90,
                width: 90,
                objectFit: "contain",
                filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.1))"
              }}
            />
            <Box>
              <Typography 
                variant="h5" 
                sx={{ 
                  fontWeight: 800, 
                  whiteSpace: "nowrap", 
                  lineHeight: 1.1,
                  background: "linear-gradient(135deg, #1976d2 0%, #00acc1 50%, #ffb300 100%)",
                  backgroundClip: "text",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  textShadow: "0 1px 2px rgba(0,0,0,0.1)"
                }}
              >
                LLILA
              </Typography>
              <Typography 
                variant="caption" 
                sx={{ 
                  color: "rgba(0,0,0,0.7)", 
                  fontSize: "0.75rem", 
                  lineHeight: 1.2,
                  fontWeight: 500,
                  fontStyle: "italic",
                  letterSpacing: "0.5px"
                }}
              >
                Let LLILA light the way
              </Typography>
            </Box>
          </Box>

          {/* Navigation for all users */}
          <Button component={RouterLink} to="/eos" color={isActive("/eo") || pathname === "/eos" ? "primary" : "inherit"}>EOs</Button>
          <Button component={RouterLink} to="/tasks" color={pathname === "/tasks" ? "primary" : "inherit"}>Tasks</Button>

          {/* Role-specific navigation */}
          {user?.role === "executor" && (
            <>
              <Button component={RouterLink} to="/dashboard/executor" color={isActive("/dashboard/executor") ? "primary" : "inherit"}>Dashboard</Button>
            </>
          )}

          {user?.role === "admin" && (
            <>
              <Button component={RouterLink} to="/dashboard/admin" color={isActive("/dashboard/admin") ? "primary" : "inherit"}>CFO Console</Button>
            </>
          )}

          {user?.role === "reviewer" && (
            <>
              <Button component={RouterLink} to="/dashboard/reviewer" color={isActive("/dashboard/reviewer") ? "primary" : "inherit"}>PMO Console</Button>
            </>
          )}

          <Tooltip title={mode === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
            <IconButton onClick={toggle} color="inherit">
              {mode === "dark" ? <Brightness7Icon /> : <Brightness4Icon />}
            </IconButton>
          </Tooltip>

          {isAuthenticated ? (
            <Button onClick={handleLogout} color="inherit">Logout</Button>
          ) : (
            <Button component={RouterLink} to="/login" color="inherit">Login</Button>
          )}
        </Toolbar>
      </AppBar>

      <Box sx={{ flex: 1 }}>
        <Container sx={{ py: 3 }}>
          <PageFade key={pathname}>{children}</PageFade>
        </Container>
      </Box>

      <Footer />
    </Box>
  );
}
