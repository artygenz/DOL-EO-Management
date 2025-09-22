import React from 'react';
import { Box, Typography, Container, Divider, Link } from '@mui/material';

export default function Footer() {
  return (
    <Box
      component="footer"
      sx={{
        mt: 'auto',
        py: 3,
        px: 2,
        backgroundColor: 'grey.50',
        borderTop: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Container maxWidth="lg">
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3, mb: 2 }}>
          {/* Company Info */}
          <Box sx={{ flex: 1, minWidth: 200 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
              <Box
                component="img"
                src="/llila-logo.jpeg"
                alt="LLILA Logo"
                sx={{
                  height: 32,
                  width: 32,
                  objectFit: "contain",
                  filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.1))"
                }}
              />
              <Typography 
                variant="h6" 
                sx={{ 
                  fontWeight: 700,
                  background: "linear-gradient(135deg, #1976d2 0%, #00acc1 50%, #ffb300 100%)",
                  backgroundClip: "text",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                LLILA
              </Typography>
            </Box>
            <Typography 
              variant="body2" 
              sx={{ 
                color: 'text.secondary',
                fontWeight: 500,
                fontStyle: 'italic',
                mb: 1
              }}
            >
              Lumen Lighthouse Intelligence Logistics Agent
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Let LLILA light the way
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Intelligent Executive Order Management System for the U.S. Department of Labor
            </Typography>
          </Box>

          {/* Quick Links */}
          <Box sx={{ flex: 1, minWidth: 150 }}>
            <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1, color: 'text.primary' }}>
              Quick Links
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              <Link href="/eos" color="text.secondary" underline="hover" sx={{ fontSize: '0.875rem' }}>
                Executive Orders
              </Link>
              <Link href="/tasks" color="text.secondary" underline="hover" sx={{ fontSize: '0.875rem' }}>
                Tasks
              </Link>
              <Link href="/dashboard" color="text.secondary" underline="hover" sx={{ fontSize: '0.875rem' }}>
                Dashboard
              </Link>
            </Box>
          </Box>

          {/* Support */}
          <Box sx={{ flex: 1, minWidth: 150 }}>
            <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1, color: 'text.primary' }}>
              Support
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem' }}>
                Email: support@lumenlighthouse.ai
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem' }}>
                Phone: (555) 123-4567
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem' }}>
                Hours: Mon-Fri 8AM-6PM EST
              </Typography>
            </Box>
          </Box>

          {/* Legal */}
          <Box sx={{ flex: 1, minWidth: 150 }}>
            <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1, color: 'text.primary' }}>
              Legal
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              <Link href="#" color="text.secondary" underline="hover" sx={{ fontSize: '0.875rem' }}>
                Privacy Policy
              </Link>
              <Link href="#" color="text.secondary" underline="hover" sx={{ fontSize: '0.875rem' }}>
                Terms of Service
              </Link>
              <Link href="#" color="text.secondary" underline="hover" sx={{ fontSize: '0.875rem' }}>
                Security Policy
              </Link>
            </Box>
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Copyright */}
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" color="text.secondary">
            © {new Date().getFullYear()} U.S. Department of Labor. All rights reserved.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Powered by LLILA Intelligence
          </Typography>
        </Box>
      </Container>
    </Box>
  );
}

