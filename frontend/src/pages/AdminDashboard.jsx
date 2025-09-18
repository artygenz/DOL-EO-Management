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
import BusinessIcon from "@mui/icons-material/Business";
import SectionHeader from "../ui/SectionHeader";
import {
  fetchDashboardStats,
  fetchEmailLogs,
} from '../store/slices/dashboardSlice';
import { useAuth } from '../hooks/useAuth';
import api from '../services/api';

export default function AdminDashboard() {
  const dispatch = useDispatch();
  const { user } = useAuth();
  const { loading, stats, error } = useSelector(
    (state) => state.dashboard
  );

  // EO assignment state
  const [executiveOrders, setExecutiveOrders] = useState([]);
  const [availableReviewers, setAvailableReviewers] = useState([]);
  const [selectedEO, setSelectedEO] = useState("");
  const [selectedReviewer, setSelectedReviewer] = useState("");
  const [assignmentDialogOpen, setAssignmentDialogOpen] = useState(false);
  const [assigningEO, setAssigningEO] = useState(false);
  
  // Available PMOs state
  const [availablePMOs, setAvailablePMOs] = useState([]);
  const [pmosLoading, setPmosLoading] = useState(false);
  const [pmosError, setPmosError] = useState("");
  
  // EO details dialog state
  const [eoDetailsDialogOpen, setEoDetailsDialogOpen] = useState(false);
  const [selectedEoForDetails, setSelectedEoForDetails] = useState(null);

  useEffect(() => {
    dispatch(fetchDashboardStats());
    dispatch(fetchEmailLogs());
    fetchAvailablePMOs();
    fetchExecutiveOrders();
    fetchAvailableReviewers();
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

  const fetchAvailableReviewers = async () => {
    try {
      const response = await api.get('/dashboard/cfo/employees');
      if (response.data.success) {
        // Filter to only show reviewers (PMOs)
        const reviewers = response.data.data.employees.filter(emp => emp.role === 'reviewer');
        setAvailableReviewers(reviewers);
      }
    } catch (err) {
      console.error('Error fetching reviewers:', err);
    }
  };

  const fetchAvailablePMOs = async () => {
    setPmosLoading(true);
    setPmosError("");
    
    try {
      const response = await api.get('/dashboard/cfo/employees');
      
      if (response.data.success) {
        // Filter to only show reviewers (PMOs)
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

  const handleEOAssignment = () => {
    if (!selectedEO || !selectedReviewer) return;
    setAssignmentDialogOpen(true);
  };

  const assignEOToReviewer = async () => {
    if (!selectedEO || !selectedReviewer) return;
    
    setAssigningEO(true);
    
    try {
      const assignmentData = {
        pmo_ids: [selectedReviewer],
        primary_pmo_id: selectedReviewer
      };
      
      const response = await api.post(`/dashboard/cfo/assign-pmos/${selectedEO}`, assignmentData);
      
      if (response.data.success) {
        // Close dialog and refresh data
        setAssignmentDialogOpen(false);
        setSelectedEO("");
        setSelectedReviewer("");
        
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
                {pmosLoading ? '...' : availablePMOs.length}
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
                System Status
              </Typography>
              <Typography variant="h6" color="success.main">
                Operational
              </Typography>
            </CardContent>
          </Card>
        </Stack>
      )}

      {/* EO Assignment Section */}
      <SectionHeader
        title="Executive Order Assignment"
        subtitle="Assign Executive Orders to Reviewers (PMOs) for management"
      />
      
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Stack spacing={3}>
            <Box>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                Assign EO to Reviewer
              </Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>
                Select an Executive Order and assign it to a Reviewer who will manage all tasks and executors.
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
                <InputLabel>Select Reviewer (PMO)</InputLabel>
                <Select
                  value={selectedReviewer}
                  onChange={(e) => setSelectedReviewer(e.target.value)}
                  label="Select Reviewer (PMO)"
                >
                  {availableReviewers.map((reviewer) => (
                    <MenuItem key={reviewer.id} value={reviewer.id}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <PeopleIcon fontSize="small" />
                        {reviewer.name} ({reviewer.org_role || 'Reviewer'})
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <Button
                variant="contained"
                onClick={handleEOAssignment}
                disabled={!selectedEO || !selectedReviewer}
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
                          Status: {eo.status} • Created: {new Date(eo.created_at).toLocaleDateString()}
                        </Typography>
                        {eo.description && (
                          <Typography color="text.secondary" variant="body2" sx={{ mt: 1 }}>
                            {eo.description.substring(0, 100)}...
                          </Typography>
                        )}
                      </Box>
                      
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip 
                          label={`${eo.tasks?.length || 0} Tasks`} 
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
        subtitle="Reviewers available for Executive Order assignments"
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
                  Available Reviewers ({availablePMOs.length})
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
                    label={`${pmo.name} (${pmo.org_role || 'Reviewer'})`}
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
                No PMOs available. Please create reviewer accounts first.
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
            Use the assignment interface above to assign Executive Orders to Reviewers, then view tasks and manage assignments.
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
              Assign Executive Order to Reviewer
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
                Selected Reviewer
              </Typography>
              {selectedReviewer && availableReviewers.find(r => r.id === selectedReviewer) && (
                <>
                  <Typography variant="body2" color="text.secondary">
                    Name: {availableReviewers.find(r => r.id === selectedReviewer)?.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Role: {availableReviewers.find(r => r.id === selectedReviewer)?.org_role || 'Reviewer'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Email: {availableReviewers.find(r => r.id === selectedReviewer)?.email}
                  </Typography>
                </>
              )}
            </Box>

            <Alert severity="info">
              <Typography variant="body2">
                This assignment will allow the selected Reviewer to:
              </Typography>
              <ul>
                <li>View all tasks from this Executive Order</li>
                <li>See which executors are assigned to each task</li>
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
            onClick={assignEOToReviewer}
            variant="contained"
            disabled={!selectedEO || !selectedReviewer || assigningEO}
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
                    {new Date(selectedEoForDetails.created_at).toLocaleDateString()}
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
                  label={`${selectedEoForDetails.tasks?.length || 0} Total Tasks`} 
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
