import React from "react";
import { AppBar, Toolbar, Typography, Button, IconButton, Tooltip, Container } from "@mui/material";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useThemeMode } from "../ui/ThemeModeProvider";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import PageFade from "../ui/PageFade";

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
    <>
      <AppBar position="sticky" elevation={0} color="inherit" sx={{ borderBottom: "1px solid", borderColor: "divider" }}>
        <Toolbar sx={{ display: "flex", gap: 1.25, minHeight: 64 }}>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700, whiteSpace: "nowrap" }}>
            U.S. DoL — AI Task Management
          </Typography>

          {/* Hide EO button for executors */}
          {user?.role !== "executor" && (
            <Button component={RouterLink} to="/eos" color={isActive("/eo") || pathname === "/eos" ? "primary" : "inherit"}>EOs</Button>
          )}

          {user?.role === "executor" && (
            <>
              <Button component={RouterLink} to="/dashboard/executor" color={isActive("/dashboard/executor") ? "primary" : "inherit"}>Dashboard</Button>
              <Button component={RouterLink} to="/my-updates" color={pathname === "/my-updates" ? "primary" : "inherit"}>Updates</Button>
            </>
          )}

          {user?.role === "admin" && (
            <>
              <Button component={RouterLink} to="/dashboard/admin" color={isActive("/dashboard/admin") ? "primary" : "inherit"}>Admin Console</Button>
              <Button component={RouterLink} to="/tasks" color={pathname === "/tasks" ? "primary" : "inherit"}>Tasks</Button>
            </>
          )}

          {user?.role === "reviewer" && (
            <>
              <Button component={RouterLink} to="/dashboard/reviewer" color={isActive("/dashboard/reviewer") ? "primary" : "inherit"}>Reviewer Console</Button>
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

      <Container sx={{ py: 3 }}>
        <PageFade key={pathname}>{children}</PageFade>
      </Container>
    </>
  );
}
