import React, { useState, useEffect, useCallback } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  Stack, Card, CardContent, Typography, Button, Chip, Alert,
  Box, FormControl, Dialog, DialogTitle, DialogContent,
  DialogActions, Divider, IconButton, Tooltip
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import AddIcon from "@mui/icons-material/Add";
import AssignmentIndIcon from "@mui/icons-material/AssignmentInd";
import SectionHeader from "../ui/SectionHeader";
import {
  fetchExecutiveOrders,
} from '../store/slices/dashboardSlice';
import { useAuth } from '../hooks/useAuth';
import api from '../services/api';
import { formatDateUSA } from '../utils/dateUtils';

export default function EOsPage() {
  const dispatch = useDispatch();
  const { user } = useAuth();
  const { executiveOrders, loading, error } = useSelector(
    (state) => state.dashboard
  );

  // PMO assignment state
  const [selectedEO, setSelectedEO] = useState(null);
  const [pmosToAssign, setPmosToAssign] = useState([]);
  const [primaryPMO, setPrimaryPMO] = useState("");
  const [assignmentDialogOpen, setAssignmentDialogOpen] = useState(false);
  const [assigningPMO, setAssigningPMO] = useState(false);
  
  // Available PMOs state
  const [availablePMOs, setAvailablePMOs] = useState([]);
  const [pmosLoading, setPmosLoading] = useState(false);
  const [pmosError, setPmosError] = useState("");
  
  // PMO assignments state
  const [pmoAssignments, setPmoAssignments] = useState([]);

  const fetchAvailablePMOs = async () => {
    setPmosLoading(true);
    setPmosError("");
    
    try {
      console.log('Fetching available PMOs...');
      const response = await api.get('/dashboard/cfo/employees');
      console.log('PMOs response:', response.data);
      
      if (response.data.success) {
        // Filter to only show PMOs
        const pmos = response.data.data.employees.filter(emp => emp.role === 'reviewer');
        console.log('Filtered PMOs:', pmos);
        setAvailablePMOs(pmos);
      } else {
        setPmosError('Failed to fetch PMOs');
      }
    } catch (err) {
      console.error('Error fetching PMOs:', err);
      setPmosError(err.response?.data?.detail || 'Failed to fetch available PMOs');
    } finally {
      setPmosLoading(false);
    }
  };

  const fetchPMOAssignments = useCallback(async () => {
    console.log('fetchPMOAssignments called with executiveOrders:', executiveOrders);
    console.log('Current user role:', user?.role);
    
    if (!executiveOrders || executiveOrders.length === 0) return;
    
    try {
      const allAssignments = [];
      
      if (user?.role === 'admin') {
        // Admin users: Fetch PMO assignments for each EO using CFO endpoint
        for (const eo of executiveOrders) {
          try {
            console.log(`Fetching PMO assignments for EO ${eo.id}`);
            const response = await api.get(`/dashboard/cfo/eo-pmo-assignments/${eo.id}`);
            console.log(`Response for EO ${eo.id}:`, response.data);
            if (response.data.success && response.data.data.assignments) {
              // Add eo_id to each assignment for easier lookup
              const assignmentsWithEOId = response.data.data.assignments.map(assignment => ({
                ...assignment,
                eo_id: eo.id
              }));
              allAssignments.push(...assignmentsWithEOId);
            }
          } catch (err) {
            console.warn(`Failed to fetch PMO assignments for EO ${eo.id}:`, err);
          }
        }
      } else if (user?.role === 'reviewer') {
        // PMO users: Use PMO-specific endpoint that includes PMO assignment info
        try {
          console.log('Fetching PMO assigned EOs with assignment info');
          const response = await api.get('/dashboard/pmo/assigned-eos');
          console.log('PMO assigned EOs response:', response.data);
          
          if (response.data.success && response.data.data.executive_orders) {
            // Extract PMO assignment info from the response
            response.data.data.executive_orders.forEach(eo => {
              if (eo.pmo_assignment) {
                allAssignments.push({
                  eo_id: eo.id,
                  pmo_name: user.name, // Current PMO user's name
                  pmo_id: user.id,
                  assigned_at: eo.pmo_assignment.assigned_at,
                  is_primary: eo.pmo_assignment.is_primary
                });
              }
            });
          }
        } catch (err) {
          console.warn('Failed to fetch PMO assigned EOs:', err);
        }
      } else {
        // Resource users: Try to get PMO info through tasks endpoint
        try {
          console.log('Fetching tasks to get PMO info for Resource user');
          const response = await api.get('/dashboard/tasks');
          console.log('Tasks response:', response.data);
          
          if (response.data.success && response.data.data.tasks) {
            // Group tasks by EO and try to infer PMO info
            const eoToPMOMap = new Map();
            
            response.data.data.tasks.forEach(task => {
              if (task.executive_order && task.executive_order.id) {
                // For Resource users, we can't get actual PMO names
                // But we can show that there is a PMO assigned
                if (!eoToPMOMap.has(task.executive_order.id)) {
                  eoToPMOMap.set(task.executive_order.id, {
                    eo_id: task.executive_order.id,
                    pmo_name: 'PMO Assigned', // Generic indicator
                    pmo_id: null,
                    assigned_at: null,
                    is_primary: false
                  });
                }
              }
            });
            
            allAssignments.push(...Array.from(eoToPMOMap.values()));
          }
        } catch (err) {
          console.warn('Failed to fetch tasks for PMO info:', err);
        }
      }
      
      console.log('All assignments collected:', allAssignments);
      setPmoAssignments(allAssignments);
    } catch (err) {
      console.error('Error fetching PMO assignments:', err);
    }
  }, [executiveOrders, user?.role, user?.id, user?.name]);

  useEffect(() => {
    dispatch(fetchExecutiveOrders());
    fetchAvailablePMOs();
  }, [dispatch]);

  useEffect(() => {
    fetchPMOAssignments();
  }, [fetchPMOAssignments]);

  const getPMONameForEO = (eoId) => {
    console.log('Getting PMO name for EO:', eoId);
    console.log('Available assignments:', pmoAssignments);
    
    const assignment = pmoAssignments.find(assignment => assignment.eo_id === eoId);
    console.log('Found assignment:', assignment);
    
    if (assignment) {
      // Use pmo_name directly from the assignment
      return assignment.pmo_name || 'Unknown PMO';
    }
    return null;
  };

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
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Simulate successful assignment
      // In real implementation, this would be an API call
      
      // Close dialog and refresh data
      setAssignmentDialogOpen(false);
      dispatch(fetchExecutiveOrders());
      
      // Show success message (you could add a snackbar here)
    } catch (error) {
      console.error('Failed to assign PMOs:', error);
      // Show error message (you could add a snackbar here)
    } finally {
      setAssigningPMO(false);
    }
  };

  const getAvailablePMOs = () => {
    return availablePMOs;
  };

  const getEOStatusColor = (status) => {
    switch (status) {
      case 'processed':
        return 'success';
      case 'pending':
        return 'warning';
      case 'received':
        return 'info';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <>
      {/* Welcome Header */}
      <Box sx={{ textAlign: 'center', py: 2, mb: 3 }}>
        <Typography variant="h4" fontWeight={700} color="primary.main">
          Executive Orders
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
          View and manage all Executive Orders
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error: {error}
        </Alert>
      )}
      
      {pmosError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          PMO Data Warning: {pmosError}
        </Alert>
      )}
      
      <SectionHeader
        title="Executive Orders"
        actions={
          <Button startIcon={<AddIcon/>}>
            New EO Intake
          </Button>
        }
      />
      
      <Stack spacing={2}>
        {(executiveOrders || []).map((eo) => (
          <Card key={eo.id} sx={{ borderRadius: 3 }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                <Box sx={{ flex: 1 }}>
                  <Typography variant="h6" fontWeight={600}>
                    {eo.title || 'Untitled'}
                  </Typography>
                  <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                    {eo.summary || 'No summary available'}
                  </Typography>
                  
                  <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                    {eo.created_at && (
                      <Typography variant="body2" color="text.secondary">
                        📅 Created: {formatDateUSA(eo.created_at)}
                      </Typography>
                    )}
                    {eo.source && (
                      <Typography variant="body2" color="text.secondary">
                        📧 Source: {eo.source}
                      </Typography>
                    )}
                    {eo.directive_count && (
                      <Typography variant="body2" color="text.secondary">
                        📋 Directives: {eo.directive_count}
                      </Typography>
                    )}
                  </Stack>
                </Box>
                
                <Stack spacing={1} alignItems="flex-end">
                  <Chip label={eo.status} size="small" color={getEOStatusColor(eo.status)} />
                  <Chip 
                    label={getPMONameForEO(eo.id) || (user?.role === 'executor' ? "PMO Assigned" : "No PMO")} 
                    size="small" 
                    variant="outlined"
                    color={getPMONameForEO(eo.id) ? "success" : "default"}
                  />
                  {eo.task_count && (
                    <Chip 
                      label={`${eo.task_count} Tasks`} 
                      size="small" 
                      variant="outlined"
                      color="info"
                    />
                  )}
                </Stack>
              </Stack>

              <Divider sx={{ my: 2 }} />

              <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }} alignItems="center">
                <Button component={RouterLink} to={`/eos/${eo.id}`} size="small" variant="outlined">
                  View Details
                </Button>
                
                {user?.role === "admin" && (
                  <Tooltip title="Assign PMOs to this Executive Order">
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={() => handlePMOAssignment(eo)}
                      sx={{ border: '1px solid', borderColor: 'divider' }}
                    >
                      <AssignmentIndIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}

                {eo.source_url && (
                  <Button size="small" variant="outlined" href={eo.source_url} target="_blank" rel="noreferrer">
                    View Original EO
                  </Button>
                )}
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>

      {(!executiveOrders || executiveOrders.length === 0) && (
        <Card>
          <CardContent>
            <Typography color="text.secondary">No executive orders found.</Typography>
          </CardContent>
        </Card>
      )}

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
                
                {pmosLoading ? (
                  <Box sx={{ textAlign: 'center', py: 3 }}>
                    <Typography>Loading available PMOs...</Typography>
                  </Box>
                ) : availablePMOs.length > 0 ? (
                  <Stack spacing={2}>
                    {availablePMOs.map((pmo) => (
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
                                {pmo.org_role || 'PMO'}
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
                ) : (
                  <Box sx={{ textAlign: 'center', py: 3 }}>
                    <Typography color="text.secondary">
                      No PMOs available. Please create PMO accounts first.
                    </Typography>
                  </Box>
                )}
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
