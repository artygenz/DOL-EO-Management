import React, { useState, useEffect, useCallback } from "react";
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
import BusinessIcon from "@mui/icons-material/Business";
import SectionHeader from "../ui/SectionHeader";
import {
  fetchDashboardStats,
  fetchEmailLogs,
} from '../store/slices/dashboardSlice';
import { useAuth } from '../hooks/useAuth';
import api from '../services/api';
import { formatDateUSA } from '../utils/dateUtils';

export default function AdminDashboard() {
  const dispatch = useDispatch();
  const { user } = useAuth();
  const { loading, stats, error } = useSelector(
    (state) => state.dashboard
  );

  // EO assignment state
  const [executiveOrders, setExecutiveOrders] = useState([]);
  const [availablePMOs, setAvailablePMOs] = useState([]);
  const [selectedEO, setSelectedEO] = useState("");
  const [selectedPMO, setSelectedPMO] = useState("");
  const [assignmentDialogOpen, setAssignmentDialogOpen] = useState(false);
  const [assigningEO, setAssigningEO] = useState(false);
  
  // PMO loading states
  const [pmosLoading, setPmosLoading] = useState(false);
  const [pmosError, setPmosError] = useState("");
  
  // PMO assignment calculations
  const [assignedPMOsCount, setAssignedPMOsCount] = useState(0);
  const [pmoAssignments, setPmoAssignments] = useState([]);
  
  // Resource data
  const [allResources, setAllResources] = useState([]);
  const [assignedResourcesCount, setAssignedResourcesCount] = useState(0);
  const [resourcesLoading, setResourcesLoading] = useState(false);
  const [resourcesError, setResourcesError] = useState("");
  
  // EO details dialog state
  const [eoDetailsDialogOpen, setEoDetailsDialogOpen] = useState(false);
  const [selectedEoForDetails, setSelectedEoForDetails] = useState(null);
  
  // All tasks data for counting
  const [allTasks, setAllTasks] = useState([]);

  useEffect(() => {
    dispatch(fetchDashboardStats());
    dispatch(fetchEmailLogs());
    fetchAvailablePMOs();
    fetchAllResources();
    fetchExecutiveOrders();
  }, [dispatch]);

  const fetchExecutiveOrders = async () => {
    try {
      const response = await api.get('/dashboard/executive-orders');
      if (response.data.success) {
        setExecutiveOrders(response.data.data.executive_orders);
      }
    } catch (err) {
      console.error('Error fetching executive orders:', err);
    }
  };

  const fetchAvailablePMOs = async () => {
    setPmosLoading(true);
    setPmosError("");
    
    try {
      const response = await api.get('/dashboard/cfo/employees');
      if (response.data.success) {
        // Filter to only show PMOs
        const pmos = response.data.data.employees.filter(emp => emp.role === 'reviewer');
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

  const fetchAllResources = async () => {
    setResourcesLoading(true);
    setResourcesError("");
    
    try {
      const response = await api.get('/dashboard/cfo/employees');
      if (response.data.success) {
        // Filter to only show resources (executors)
        const resources = response.data.data.employees.filter(emp => emp.role === 'executor');
        console.log('Filtered Resources:', resources);
        setAllResources(resources);
      } else {
        setResourcesError('Failed to fetch resources');
      }
    } catch (err) {
      console.error('Error fetching resources:', err);
      setResourcesError(err.response?.data?.detail || 'Failed to fetch resources');
    } finally {
      setResourcesLoading(false);
    }
  };


  const fetchPMOAssignments = useCallback(async () => {
    if (!executiveOrders || executiveOrders.length === 0) return;
    
    try {
      const allAssignments = [];
      
      // Fetch PMO assignments for each EO
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
      
      console.log('All PMO assignments collected in AdminDashboard:', allAssignments);
      setPmoAssignments(allAssignments);
    } catch (err) {
      console.error('Error fetching PMO assignments:', err);
    }
  }, [executiveOrders]);

  // Calculate assigned PMOs from PMO assignments data
  const calculatePMOAssignments = useCallback(() => {
    const assignedPMOIds = new Set();
    
    // Use the fetched PMO assignments data
    pmoAssignments.forEach(assignment => {
      assignedPMOIds.add(assignment.pmo_id);
    });
    
    const assignedCount = assignedPMOIds.size;
    
    setAssignedPMOsCount(assignedCount);
  }, [pmoAssignments]);

  // Calculate resource engagement
  const calculateResourceEngagement = useCallback(() => {
    if (allResources.length === 0 || allTasks.length === 0) {
      return;
    }
    
    const assignedResourceIds = new Set();
    
    allTasks.forEach(task => {
      if (task.assignee && task.assignee.id) {
        // Only count if this assignee is actually a resource (executor)
        const isResource = allResources.some(resource => resource.id === task.assignee.id);
        if (isResource) {
          assignedResourceIds.add(task.assignee.id);
        }
      }
    });
    
    setAssignedResourcesCount(assignedResourceIds.size);
  }, [allResources, allTasks]);

  // Fetch PMO assignments when executive orders change
  useEffect(() => {
    if (executiveOrders && executiveOrders.length > 0) {
      fetchPMOAssignments();
    }
  }, [fetchPMOAssignments]);

  // Calculate PMO assignments when data changes
  useEffect(() => {
    calculatePMOAssignments();
  }, [calculatePMOAssignments]);

  // Fetch all tasks for EO counting
  useEffect(() => {
    const fetchAllTasks = async () => {
      try {
        const response = await api.get('/dashboard/cfo/tasks?limit=1000');
        if (response.data.success) {
          const tasks = response.data.data.tasks || [];
          setAllTasks(tasks);
        }
      } catch (err) {
        console.error('Error fetching all tasks:', err);
      }
    };
    
    fetchAllTasks();
  }, []);

  // Calculate resource engagement when resources or tasks change
  useEffect(() => {
    calculateResourceEngagement();
  }, [calculateResourceEngagement]);

  // Helper function to count tasks for a specific EO
  const getTaskCountForEO = (eoId) => {
    return allTasks.filter(task => {
      if (!task.executive_order) return false;
      // Handle both string and number comparisons
      return task.executive_order.id === eoId || task.executive_order.id === String(eoId) || String(task.executive_order.id) === eoId;
    }).length;
  };

  // Helper function to get PMO name for a specific EO
  const getPMONameForEO = (eoId) => {
    console.log(`Looking for PMO for EO ${eoId}`);
    console.log('Available pmoAssignments:', pmoAssignments);
    const assignment = pmoAssignments.find(assignment => assignment.eo_id === eoId);
    console.log(`Found assignment for EO ${eoId}:`, assignment);
    if (assignment) {
      return assignment.pmo_name || 'Unknown PMO';
    }
    return null;
  };

  const handleEOAssignment = () => {
    if (!selectedEO || !selectedPMO) return;
    setAssignmentDialogOpen(true);
  };

  const assignEOToPMO = async () => {
    if (!selectedEO || !selectedPMO) return;
    
    setAssigningEO(true);
    
    try {
      const assignmentData = {
        pmo_ids: [selectedPMO],
        primary_pmo_id: selectedPMO
      };
      
      const response = await api.post(`/dashboard/cfo/assign-pmos/${selectedEO}`, assignmentData);
      
      if (response.data.success) {
        // Close dialog and refresh data
        setAssignmentDialogOpen(false);
        setSelectedEO("");
        setSelectedPMO("");
        
        // Refresh data to show updated assignments
        fetchExecutiveOrders();
        fetchAvailablePMOs();
        
        // Show success message (you could add a snackbar here)
        console.log('EO assigned successfully!');
      }
    } catch (error) {
      console.error('Failed to assign EO:', error);
      // Show error message (you could add a snackbar here)
    } finally {
      setAssigningEO(false);
    }
  };

  const getAvailablePMOs = () => {
    return availablePMOs;
  };
  
  const truncateTitle = (title, maxLength = 60) => {
    if (title.length <= maxLength) return title;
    return title.substring(0, maxLength) + '...';
  };
  
  const handleViewFullEO = (eo) => {
    setSelectedEoForDetails(eo);
    setEoDetailsDialogOpen(true);
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
      
      {pmosError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          PMO Data Warning: {pmosError}
        </Alert>
      )}
      
      {resourcesError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Resource Data Warning: {resourcesError}
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
                Active PMOs Engaged
              </Typography>
              <Typography variant="h4" color="primary.main">
                {pmosLoading ? '...' : `${assignedPMOsCount}/${availablePMOs.length}`}
              </Typography>
              {pmosLoading && (
                <Typography variant="caption" color="text.secondary">
                  Loading PMOs...
                </Typography>
              )}
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography color="text.secondary" gutterBottom>
                Active Resources Engaged
              </Typography>
              <Typography variant="h4" color="secondary.main">
                {resourcesLoading ? '...' : `${assignedResourcesCount || 0}/${allResources.length || 0}`}
              </Typography>
              {resourcesLoading && (
                <Typography variant="caption" color="text.secondary">
                  Loading Resources...
                </Typography>
              )}
            </CardContent>
          </Card>
          
        </Stack>
      )}

      {/* EO Assignment Section */}
      <SectionHeader
        title="Executive Order Assignment"
        subtitle="Assign Executive Orders to PMOs for management"
      />
      
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Stack spacing={3}>
            <Box>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                Assign EO to PMO
              </Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>
                Select an Executive Order and assign it to a PMO who will manage all tasks and resources.
              </Typography>
            </Box>
            
            <Stack direction="row" spacing={2} alignItems="center">
              <FormControl sx={{ minWidth: 300 }}>
                <InputLabel>Select Executive Order</InputLabel>
                <Select
                  value={selectedEO}
                  onChange={(e) => setSelectedEO(e.target.value)}
                  label="Select Executive Order"
                >
                  {executiveOrders.map((eo) => (
                    <MenuItem key={eo.id} value={eo.id}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <BusinessIcon fontSize="small" />
                        {eo.title}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <FormControl sx={{ minWidth: 300 }}>
                <InputLabel>Select PMO</InputLabel>
                <Select
                  value={selectedPMO}
                  onChange={(e) => setSelectedPMO(e.target.value)}
                  label="Select PMO"
                >
                  {availablePMOs.map((pmo) => (
                    <MenuItem key={pmo.id} value={pmo.id}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <PeopleIcon fontSize="small" />
                        {pmo.name} ({pmo.org_role || 'PMO'})
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <Button
                variant="contained"
                onClick={handleEOAssignment}
                disabled={!selectedEO || !selectedPMO}
                startIcon={<AssignmentIndIcon />}
              >
                Assign EO
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* Current EO Assignments */}
      <SectionHeader
        title="Current EO Assignments"
        subtitle="View and manage existing Executive Order assignments"
      />
      
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          {executiveOrders.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 2 }}>
              <Typography color="text.secondary">
                No Executive Orders found in the system.
              </Typography>
            </Box>
          ) : (
            <Stack spacing={2}>
              {executiveOrders.map((eo) => (
                <Card key={eo.id} variant="outlined">
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Box sx={{ flex: 1 }}>
                        <Stack direction="row" alignItems="center" spacing={1}>
                          <Typography variant="h6" fontWeight={600}>
                            {truncateTitle(eo.title)}
                          </Typography>
                          {eo.title.length > 60 && (
                            <Button
                              size="small"
                              variant="text"
                              color="primary"
                              onClick={() => handleViewFullEO(eo)}
                              sx={{ minWidth: 'auto', p: 0.5 }}
                            >
                              View Full EO
                            </Button>
                          )}
                        </Stack>
                        <Typography color="text.secondary" variant="body2">
                          Status: {eo.status} • Created: {formatDateUSA(eo.created_at)}
                        </Typography>
                        {eo.description && (
                          <Typography color="text.secondary" variant="body2" sx={{ mt: 1 }}>
                            {eo.description.substring(0, 100)}...
                          </Typography>
                        )}
                      </Box>
                      
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip 
                          label={getPMONameForEO(eo.id) || "No PMO"} 
                          size="small" 
                          color={getPMONameForEO(eo.id) ? "success" : "default"}
                          variant="outlined"
                        />
                        <Chip 
                          label={`${getTaskCountForEO(eo.id)} Tasks`} 
                          size="small" 
                          color="primary" 
                          variant="outlined"
                        />
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => {
                            setSelectedEO(eo.id);
                            setAssignmentDialogOpen(true);
                          }}
                        >
                          Manage Assignment
                        </Button>
                      </Stack>
                    </Stack>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>

      {/* Tasks are now shown on the dedicated Tasks page */}
      <SectionHeader
        title="Quick Access"
        subtitle="Navigate to different sections of the system"
      />
      
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={2}>
            <Button
              component={RouterLink}
              to="/tasks"
              variant="contained"
              startIcon={<AssignmentIndIcon />}
            >
              View All Tasks
            </Button>
            <Button
              component={RouterLink}
              to="/eos"
              variant="outlined"
            >
              View Executive Orders
            </Button>
          </Stack>
        </CardContent>
      </Card>
      
      {/* PMO Assignment Overview */}
      {/* Available PMOs Section */}
      <SectionHeader
        title="Available PMOs"
        subtitle="PMOs available for Executive Order assignments"
      />
      
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          {pmosLoading ? (
            <Box sx={{ textAlign: 'center', py: 2 }}>
              <Typography>Loading available PMOs...</Typography>
            </Box>
          ) : availablePMOs.length > 0 ? (
            <Stack spacing={2}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6" fontWeight={600}>
                  Available PMOs ({availablePMOs.length})
                </Typography>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={fetchAvailablePMOs}
                  disabled={pmosLoading}
                  startIcon={<PeopleIcon />}
                >
                  Refresh
                </Button>
              </Box>
              <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
                {availablePMOs.map((pmo) => (
                  <Chip
                    key={pmo.id}
                    label={`${pmo.name} (${pmo.org_role || 'PMO'})`}
                    variant="outlined"
                    color="primary"
                    icon={<PeopleIcon />}
                    sx={{ mb: 1 }}
                  />
                ))}
              </Stack>
            </Stack>
          ) : (
            <Box sx={{ textAlign: 'center', py: 2 }}>
              <Typography color="text.secondary">
                No PMOs available. Please create PMO accounts first.
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

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
            Use the assignment interface above to assign Executive Orders to PMOs, then view tasks and manage assignments.
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

      {/* EO Assignment Dialog */}
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
              Assign Executive Order to PMO
            </Typography>
          </Stack>
        </DialogTitle>
        
        <DialogContent>
          <Stack spacing={3}>
            <Box>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                Executive Order Details
              </Typography>
              {selectedEO && executiveOrders.find(eo => eo.id === selectedEO) && (
                <>
                  <Typography variant="body2" color="text.secondary">
                    {executiveOrders.find(eo => eo.id === selectedEO)?.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    ID: {selectedEO}
                  </Typography>
                </>
              )}
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                Selected PMO
              </Typography>
              {selectedPMO && availablePMOs.find(p => p.id === selectedPMO) && (
                <>
                  <Typography variant="body2" color="text.secondary">
                    Name: {availablePMOs.find(p => p.id === selectedPMO)?.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Role: {availablePMOs.find(p => p.id === selectedPMO)?.org_role || 'PMO'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Email: {availablePMOs.find(p => p.id === selectedPMO)?.email}
                  </Typography>
                </>
              )}
            </Box>

            <Alert severity="info">
              <Typography variant="body2">
                This assignment will allow the selected PMO to:
              </Typography>
              <ul>
                <li>View all tasks from this Executive Order</li>
                <li>See which resources are assigned to each task</li>
                <li>Monitor task progress and daily updates</li>
                <li>Manage task assignments and approvals</li>
              </ul>
            </Alert>
          </Stack>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setAssignmentDialogOpen(false)} disabled={assigningEO}>
            Cancel
          </Button>
          <Button 
            onClick={assignEOToPMO}
            variant="contained"
            disabled={!selectedEO || !selectedPMO || assigningEO}
            startIcon={assigningEO ? null : <AssignmentIndIcon />}
          >
            {assigningEO ? 'Assigning...' : 'Assign Executive Order'}
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* EO Details Dialog */}
      <Dialog 
        open={eoDetailsDialogOpen} 
        onClose={() => setEoDetailsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Stack direction="row" spacing={1} alignItems="center">
            <BusinessIcon color="primary" />
            <Typography variant="h6">
              Executive Order Details
            </Typography>
          </Stack>
        </DialogTitle>
        
        <DialogContent>
          {selectedEoForDetails && (
            <Stack spacing={3}>
              <Box>
                <Typography variant="h5" fontWeight={600} gutterBottom>
                  {selectedEoForDetails.title}
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                  {selectedEoForDetails.description || 'No description available'}
                </Typography>
              </Box>
              
              <Divider />
              
              <Stack direction="row" spacing={3}>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Status
                  </Typography>
                  <Chip 
                    label={selectedEoForDetails.status} 
                    color={selectedEoForDetails.status === 'processed' ? 'success' : 'default'}
                    size="small"
                  />
                </Box>
                
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Created
                  </Typography>
                  <Typography variant="body2">
                    {formatDateUSA(selectedEoForDetails.created_at)}
                  </Typography>
                </Box>
                
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Message ID
                  </Typography>
                  <Typography variant="body2" fontFamily="monospace">
                    {selectedEoForDetails.message_id}
                  </Typography>
                </Box>
              </Stack>
              
              <Divider />
              
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Tasks
                </Typography>
                <Chip 
                  label={`${getTaskCountForEO(selectedEoForDetails.id)} Total Tasks`} 
                  color="primary"
                  size="medium"
                />
              </Box>
            </Stack>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setEoDetailsDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
