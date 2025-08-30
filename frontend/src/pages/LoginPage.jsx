import React, { useState } from "react";
import { Card, CardContent, Typography, Button, Stack, TextField, Alert } from "@mui/material";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { login } from "../store/slices/authSlice";
import LoadingSpinner from "../components/common/LoadingSpinner";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { loading, error } = useSelector((state) => state.auth);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const result = await dispatch(login({ email, password }));
    if (login.fulfilled.match(result)) {
      // Navigate to dashboard, which will redirect to appropriate role-based dashboard
      navigate("/dashboard");
    }
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <Card sx={{ maxWidth: 480, mx: "auto", mt: 8 }}>
      <CardContent>
        <Typography variant="h5" fontWeight={700} gutterBottom>
          Secure Access
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          Sign in to access your dashboard.
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Stack spacing={2}>
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              fullWidth
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              fullWidth
            />
            <Button type="submit" fullWidth>
              Sign In
            </Button>
          </Stack>
        </form>

        <Typography color="text.secondary" sx={{ mt: 2, fontSize: "0.875rem" }}>
          Demo credentials: jack.smith@lumenlighthouse.ai / Lumen@2025
        </Typography>
      </CardContent>
    </Card>
  );
}
