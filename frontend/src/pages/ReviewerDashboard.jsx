import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  Stack, Card, CardContent, Typography, Button, Chip, Alert,
  Box, FormControl, InputLabel, Select, Dialog, DialogTitle, DialogContent,
  DialogActions, Divider, IconButton, Tooltip, Avatar, AvatarGroup, MenuItem
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import AssignmentIndIcon from "@mui/icons-material/AssignmentInd";
import PeopleIcon from "@mui/icons-material/People";
import TaskIcon from "@mui/icons-material/Task";
import SectionHeader from "../ui/SectionHeader";
import {
  fetchDashboardStats,
  fetchExecutiveOrders,
} from '../store/slices/dashboardSlice';
import { assignTaskToExecutor } from '../store/slices/taskSlice';
import { useAuth } from '../hooks/useAuth';

export default function ReviewerDashboard() {
  const dispatch = useDispatch();
  const { user } = useAuth();
  const { loading, stats, error, executiveOrders } = useSelector(
    (state) => state.dashboard
  );

  // Task assignment state
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedAssignee, setSelectedAssignee] = useState("");
  const [assignmentDialogOpen, setAssignmentDialogOpen] = useState(false);
  const [assigningTask, setAssigningTask] = useState(false);

  // Debug logging
  console.log('ReviewerDashboard State:', { loading, stats, error, executiveOrders });

  useEffect(() => {
    dispatch(fetchDashboardStats());
    dispatch(fetchExecutiveOrders());
  }, [dispatch]);

  const handleTaskAssignment = (task) => {
    setSelectedTask(task);
    setSelectedAssignee(task.assignee_id || "");
    setAssignmentDialogOpen(true);
  };

  const handleTaskAssignmentToExecutor = async () => {
    if (!selectedAssignee) return;
    
    setAssigningTask(true);
    
    try {
      // Call the real API endpoint
      await dispatch(assignTaskToExecutor({
        taskId: selectedTask.id,
        assigneeId: selectedAssignee
      })).unwrap();
      
      console.log('✅ Task assigned successfully!');
      
      // Close dialog and refresh data
      setAssignmentDialogOpen(false);
      dispatch(fetchExecutiveOrders());
      
      // Show success message (you could add a snackbar here)
    } catch (error) {
      console.error('Failed to assign task:', error);
      // Show error message (you could add a snackbar here)
    } finally {
      setAssigningTask(false);
    }
  };

  const getAvailableExecutors = () => {
    // TODO: Fetch available executors from backend endpoint: /dashboard/pmo/employees
    // For now, return mock data based on org_role
    // In the future, this will call the real API to get executors under this PMO
    return [
      { id: 'exec1', name: 'Dylan Sachetti', role: 'Director of Compliance', email: 'Dylan.Sachetti@lumenlighthouse.ai' },
      { id: 'exec2', name: 'Ayesha Ahsan', role: 'Director of Division of Business Process Improvement', email: 'Ayesha.Ahsan@lumenlighthouse.ai' },
      { id: 'exec3', name: 'Hibbi Iqbal', role: 'Director of Financial Reporting', email: 'Hibbi.Iqbal@lumenlighthouse.ai' },
      { id: 'exec4', name: 'Robert Springfiled', role: 'Director of Security and Technology', email: 'Robert.Springfiled@lumenlighthouse.ai' },
      { id: 'exec5', name: 'Sophia Carty', role: 'Director of Accounting', email: 'Sophia.Carty@lumenlighthouse.ai' }
    ];
  };

  const getTaskStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'in_progress': return 'warning';
      case 'approved': return 'success';
      case 'rejected': return 'error';
      default: return 'default';
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
          Welcome back, {user?.name?.split(' ')[0] || 'Reviewer'}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
          Manage your assigned Executive Orders and team
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
                Assigned EOs
              </Typography>
              <Typography variant="h4" color="primary.main">
                {stats.executive_orders?.total || 0}
              </Typography>
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography color="text.secondary" gutterBottom>
                Team Members
              </Typography>
              <Typography variant="h4" color="info.main">
                {getAvailableExecutors().length}
              </Typography>
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography color="text.secondary" gutterBottom>
                Active Tasks
              </Typography>
              <Typography variant="h4" color="secondary.main">
                {stats.tasks?.total || 0}
              </Typography>
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography color="text.secondary" gutterBottom>
                Team Status
              </Typography>
              <Typography variant="h6" color="success.main">
                Active
              </Typography>
            </CardContent>
          </Card>
        </Stack>
      )}

      {/* Team Overview */}
      <SectionHeader
        title="Your Team"
        subtitle="Executors under your supervision"
      />
      
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Stack spacing={2}>
            {getAvailableExecutors().map((executor) => (
              <Box key={executor.id} sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'space-between',
                p: 2,
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 2
              }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Avatar sx={{ bgcolor: 'primary.main' }}>
                    {executor.name.split(' ').map(n => n[0]).join('')}
                  </Avatar>
                  <Box>
                    <Typography variant="subtitle1" fontWeight={600}>
                      {executor.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {executor.role}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {executor.email}
                    </Typography>
                  </Box>
                </Box>
                
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip 
                    label="Active" 
                    size="small" 
                    color="success" 
                    variant="outlined"
                  />
                  <Button 
                    component={RouterLink} 
                    to={`/tasks?assignee=${executor.id}`} 
                    size="small" 
                    variant="outlined"
                  >
                    View Tasks
                  </Button>
                </Box>
              </Box>
            ))}
          </Stack>
        </CardContent>
      </Card>

      {/* Assigned Executive Orders */}
      <SectionHeader
        title="Your Executive Orders"
        subtitle="EOs assigned to you for management"
      />
      
      {/* 
        TODO: EO Mapping Logic
        Currently: Shows all EOs from /dashboard/executive-orders endpoint
        Should: Filter EOs based on eo_pmo_assignments table where pmo_id = current_user.id
        
        Backend endpoint: /dashboard/executive-orders already exists but needs role-based filtering
        Database: eo_pmo_assignments table links EOs to PMOs (reviewers)
        
        When admin assigns PMO to EO:
        1. Creates record in eo_pmo_assignments table
        2. Reviewer dashboard should only show EOs where they are assigned as PMO
        3. Current endpoint returns all EOs - needs backend update for role-based filtering
      */}
      
      {executiveOrders && executiveOrders.length > 0 ? (
        <Stack spacing={2}>
          {executiveOrders.map((eo) => (
            <Card key={eo.id} sx={{ borderRadius: 3 }}>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="h6" fontWeight={600}>
                      {eo.title || 'Untitled EO'}
                    </Typography>
                    <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                      ID: {eo.id}
                    </Typography>
                    <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                      Created: {new Date(eo.created_at).toLocaleDateString()}
                    </Typography>
                    <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                      Tasks: {eo.task_count || 0}
                    </Typography>
                  </Box>
                  
                  <Stack spacing={1} alignItems="flex-end">
                    <Chip 
                      label={eo.status || 'Unknown'} 
                      size="small" 
                      color={eo.status === 'processed' ? 'success' : 'default'}
                    />
                    <Button 
                      component={RouterLink} 
                      to={`/eos/${eo.id}`} 
                      size="small" 
                      variant="outlined"
                    >
                      View Details
                    </Button>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>
      ) : (
        <Card>
          <CardContent>
            <Typography color="text.secondary" textAlign="center">
              No executive orders assigned to you yet.
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* Task Management Section */}
      <SectionHeader
        title="Task Management"
        subtitle="Assign and manage tasks for your team"
      />
      
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Quick Actions
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Use the navigation buttons above to view and manage tasks, or assign new tasks to your team members.
          </Typography>
          <Stack direction="row" spacing={2}>
            <Button 
              component={RouterLink} 
              to="/tasks" 
              variant="contained" 
              startIcon={<TaskIcon/>}
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

      {/* Unassigned Tasks Section */}
      <SectionHeader
        title="Unassigned Tasks"
        subtitle="Tasks that need to be assigned to team members"
      />
      
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Typography color="text.secondary" textAlign="center">
            This section will show tasks that need assignment. Currently using mock data - will be connected to backend.
          </Typography>
          <Typography variant="body2" color="text.secondary" textAlign="center" sx={{ mt: 1 }}>
            In the future, you'll be able to assign these tasks directly to your team members.
          </Typography>
        </CardContent>
      </Card>

      {/* Task Assignment Dialog */}
      <Dialog 
        open={assignmentDialogOpen} 
        onClose={() => setAssignmentDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Stack direction="row" spacing={1} alignItems="center">
            <AssignmentIndIcon color="primary" />
            <Typography variant="h6">
              Assign Task to Executor
            </Typography>
          </Stack>
        </DialogTitle>
        
        <DialogContent>
          {selectedTask && (
            <Stack spacing={3}>
              <Box>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Task Details
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {selectedTask.title || 'Untitled Task'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  ID: {selectedTask.id}
                </Typography>
              </Box>

              <Divider />

              <Box>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Select Executor
                </Typography>
                <FormControl fullWidth>
                  <InputLabel>Assign to</InputLabel>
                  <Select
                    value={selectedAssignee}
                    onChange={(e) => setSelectedAssignee(e.target.value)}
                    label="Assign to"
                  >
                    {getAvailableExecutors().map((executor) => (
                      <MenuItem key={executor.id} value={executor.id}>
                        {executor.name} - {executor.role}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Box>
            </Stack>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setAssignmentDialogOpen(false)} disabled={assigningTask}>
            Cancel
          </Button>
          <Button 
            onClick={handleTaskAssignmentToExecutor}
            variant="contained"
            disabled={!selectedAssignee || assigningTask}
            startIcon={assigningTask ? null : <AssignmentIndIcon />}
          >
            {assigningTask ? 'Assigning...' : 'Assign Task'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
