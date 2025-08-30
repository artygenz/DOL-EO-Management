import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  Stack, Card, CardContent, Typography, Button, Chip, TextField, MenuItem, Alert,
  Box, FormControl, InputLabel, Select, Dialog, DialogTitle, DialogContent,
  DialogActions, Divider, IconButton, Tooltip
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import AddIcon from "@mui/icons-material/Add";
import AssignmentIndIcon from "@mui/icons-material/AssignmentInd";
import PeopleIcon from "@mui/icons-material/People";
import SectionHeader from "../ui/SectionHeader";
import {
  fetchDashboardStats,
  fetchEmailLogs,
} from '../store/slices/dashboardSlice';
import { useAuth } from '../hooks/useAuth';

export default function AdminDashboard() {
  const dispatch = useDispatch();
  const { user } = useAuth();
  const { loading, stats, error } = useSelector(
    (state) => state.dashboard
  );

  // PMO assignment state
  const [selectedEO, setSelectedEO] = useState(null);
  const [pmosToAssign, setPmosToAssign] = useState([]);
  const [primaryPMO, setPrimaryPMO] = useState("");
  const [assignmentDialogOpen, setAssignmentDialogOpen] = useState(false);
  const [assigningPMO, setAssigningPMO] = useState(false);

  // Debug logging
  console.log('AdminDashboard State:', { loading, stats, error });

  useEffect(() => {
    dispatch(fetchDashboardStats());
    dispatch(fetchEmailLogs());
  }, [dispatch]);

  const handlePMOAssignment = (eo) => {
    setSelectedEO(eo);
    setPmosToAssign([]);
    setPrimaryPMO("");
    setAssignmentDialogOpen(true);
  };

  const assignPMOsToEO = async () => {
    if (pmosToAssign.length === 0) return;
    
    setAssigningPMO(true);
    
    try {
      // TODO: Implement PMO assignment API call
      // This would call an endpoint like: POST /dashboard/assign-pmo
      console.log('Assigning PMOs to EO:', {
        eoId: selectedEO.id,
        pmos: pmosToAssign,
        primaryPMO,
        assignedBy: user?.id,
        assignmentDate: new Date().toISOString()
      });
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Simulate successful assignment
      // In real implementation, this would be an API call
      console.log('✅ PMOs assigned successfully!');
      
      // Close dialog and refresh data
      setAssignmentDialogOpen(false);
      
      // Show success message (you could add a snackbar here)
    } catch (error) {
      console.error('Failed to assign PMOs:', error);
      // Show error message (you could add a snackbar here)
    } finally {
      setAssigningPMO(false);
    }
  };

  const getAvailablePMOs = () => {
    // TODO: Fetch available PMOs from backend
    // For now, return mock data
    return [
      { id: 'pm1', name: 'Sarah Johnson', role: 'Senior Project Manager' },
      { id: 'pm2', name: 'David Chen', role: 'Compliance Manager' },
      { id: 'pm3', name: 'Maria Rodriguez', role: 'Financial Operations Manager' },
      { id: 'pm4', name: 'EO 14249 Email', role: 'EO 14249 Email' },
      { id: 'pm5', name: 'EO 14247 Email', role: 'EO 14247 Email' }
    ];
  };



  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <>
      {/* Welcome Header */}
      <Box sx={{ textAlign: 'center', py: 2, mb: 3 }}>
        <Typography variant="h4" fontWeight={700} color="primary.main">
          Welcome back, {user?.name?.split(' ')[0] || 'Administrator'}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
          Manage Executive Orders and PMO assignments
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error: {error}
        </Alert>
      )}
      
      {stats && (
        <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography color="text.secondary" gutterBottom>
                Total Executive Orders
              </Typography>
              <Typography variant="h4" color="primary.main">
                {stats.executive_orders?.total || 0}
              </Typography>
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography color="text.secondary" gutterBottom>
                Total Tasks
              </Typography>
              <Typography variant="h4" color="info.main">
                {stats.tasks?.total || 0}
              </Typography>
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography color="text.secondary" gutterBottom>
                Active PMOs
              </Typography>
              <Typography variant="h4" color="secondary.main">
                {getAvailablePMOs().length}
              </Typography>
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography color="text.secondary" gutterBottom>
                System Status
              </Typography>
              <Typography variant="h6" color="success.main">
                Operational
              </Typography>
            </CardContent>
          </Card>
        </Stack>
      )}
      
            {/* PMO Assignment Overview */}
      <SectionHeader
        title="PMO Assignment Management"
        subtitle="Assign and manage PMOs for Executive Orders"
      />
      
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Quick Actions
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Use the navigation buttons above to view Executive Orders and Tasks, then assign PMOs as needed.
          </Typography>
          <Stack direction="row" spacing={2}>
            <Button 
              component={RouterLink} 
              to="/eos" 
              variant="contained" 
              startIcon={<AddIcon/>}
            >
              View Executive Orders
            </Button>
                                           <Button 
                   component={RouterLink} 
                   to="/tasks" 
                   variant="outlined"
                 >
                   View Tasks
                 </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* PMO Assignment Dialog */}
      <Dialog 
        open={assignmentDialogOpen} 
        onClose={() => setAssignmentDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Stack direction="row" spacing={1} alignItems="center">
            <AssignmentIndIcon color="primary" />
            <Typography variant="h6">
              Assign PMOs to Executive Order
            </Typography>
          </Stack>
        </DialogTitle>
        
        <DialogContent>
          {selectedEO && (
            <Stack spacing={3}>
              <Box>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Executive Order Details
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {selectedEO.title || 'Untitled EO'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  ID: {selectedEO.id}
                </Typography>
              </Box>

              <Divider />

              <Box>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Select PMOs to Assign
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Choose one or more PMOs to oversee this Executive Order. The first PMO will be designated as primary.
                </Typography>
                
                <Stack spacing={2}>
                  {getAvailablePMOs().map((pmo) => (
                    <Card key={pmo.id} variant="outlined">
                      <CardContent sx={{ py: 1.5, px: 2 }}>
                        <Stack direction="row" spacing={2} alignItems="center">
                          <FormControl size="small">
                            <input
                              type="checkbox"
                              checked={pmosToAssign.includes(pmo.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setPmosToAssign([...pmosToAssign, pmo.id]);
                                  if (pmosToAssign.length === 0) {
                                    setPrimaryPMO(pmo.id);
                                  }
                                } else {
                                  setPmosToAssign(pmosToAssign.filter(id => id !== pmo.id));
                                  if (primaryPMO === pmo.id) {
                                    setPrimaryPMO(pmosToAssign.length > 1 ? pmosToAssign[1] : "");
                                  }
                                }
                              }}
                            />
                          </FormControl>
                          
                          <Box sx={{ flex: 1 }}>
                            <Typography variant="body2" fontWeight={600}>
                              {pmo.name}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {pmo.role}
                            </Typography>
                          </Box>
                          
                          {pmosToAssign.includes(pmo.id) && (
                            <FormControl size="small">
                              <input
                                type="radio"
                                name="primaryPMO"
                                checked={primaryPMO === pmo.id}
                                onChange={() => setPrimaryPMO(pmo.id)}
                              />
                              <Typography variant="caption" color="primary">
                                Primary
                              </Typography>
                            </FormControl>
                          )}
                        </Stack>
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
              </Box>
            </Stack>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setAssignmentDialogOpen(false)} disabled={assigningPMO}>
            Cancel
          </Button>
          <Button 
            onClick={assignPMOsToEO}
            variant="contained"
            disabled={pmosToAssign.length === 0 || assigningPMO}
            startIcon={assigningPMO ? null : <AssignmentIndIcon />}
          >
            {assigningPMO ? 'Assigning...' : `Assign ${pmosToAssign.length} PMO${pmosToAssign.length !== 1 ? 's' : ''}`}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
