import React from "react";
import { Stack, Typography } from "@mui/material";

export default function SectionHeader({ title, actions = null }) {
  return (
    <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
      <Typography variant="h6" fontWeight={700}>{title}</Typography>
      <Stack direction="row" spacing={1}>{actions}</Stack>
    </Stack>
  );
}
