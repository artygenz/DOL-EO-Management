import React, { useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  Button,
  Stack,
  TextField,
  Snackbar,
  Alert,
  CircularProgress,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showToast, setShowToast] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setShowToast(false);

    try {
      const response = await api.post("/auth/login", { email, password });
      
      // Store token
      localStorage.setItem("token", response.data.access_token);
      
      // Navigate to dashboard
      navigate("/dashboard");
      
    } catch (err) {
      console.log("Login error:", err);
      
      // Get error message
      let errorMessage = "Invalid email or password";
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      console.log("Setting error message:", errorMessage);
      setError(errorMessage);
      setShowToast(true);
      console.log("Toast should now be visible:", true);
      console.log("Current error state:", errorMessage);
      console.log("Current toast state:", true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card sx={{ maxWidth: 480, mx: "auto", mt: 8 }}>
      <CardContent>
        <Typography variant="h5" fontWeight={700} gutterBottom>
          Secure Access
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          Sign in to access your dashboard.
        </Typography>

        <form onSubmit={handleSubmit} noValidate>
          <Stack spacing={2}>
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              fullWidth
              autoComplete="email"
              disabled={loading}
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              fullWidth
              autoComplete="current-password"
              disabled={loading}
            />

            <Button
              type="submit"
              variant="contained"
              fullWidth
              disabled={loading}
              startIcon={
                loading ? <CircularProgress size={16} thickness={5} /> : null
              }
            >
              {loading ? "Signing in…" : "Sign In"}
            </Button>
          </Stack>
        </form>

      </CardContent>

      {/* Global top notification - positioned like navbar */}
      <Snackbar
        open={showToast}
        onClose={() => setShowToast(false)}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
        sx={{
          '& .MuiSnackbar-root': {
            top: '20px !important',
            left: '50% !important',
            transform: 'translateX(-50%) !important',
            right: 'auto !important',
          }
        }}
      >
        <Alert
          severity="error"
          variant="filled"
          onClose={() => setShowToast(false)}
          sx={{
            width: '100%',
            minWidth: '400px',
            maxWidth: '600px',
            borderRadius: '8px',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
            background: '#d32f2f',
            '& .MuiAlert-message': {
              fontSize: '14px',
              fontWeight: 500,
            }
          }}
        >
          {error}
        </Alert>
      </Snackbar>
    </Card>
  );
}
