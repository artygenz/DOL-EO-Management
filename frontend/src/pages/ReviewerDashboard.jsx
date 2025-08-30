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
import BusinessIcon from "@mui/icons-material/Business";
import SectionHeader from "../ui/SectionHeader";
import {
  fetchDashboardStats,
  fetchExecutiveOrders,
} from '../store/slices/dashboardSlice';
import { assignTaskToExecutor } from '../store/slices/taskSlice';
import { useAuth } from '../hooks/useAuth';
import api from '../services/api';

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
  
  // EO management state
  const [assignedEOs, setAssignedEOs] = useState([]);
  const [assignedEOsWithTasks, setAssignedEOsWithTasks] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [pmosLoading, setPmosLoading] = useState(false);
  const [pmosError, setPmosError] = useState("");
  
  // EO details dialog state
  const [eoDetailsDialogOpen, setEoDetailsDialogOpen] = useState(false);
  const [selectedEoForDetails, setSelectedEoForDetails] = useState(null);

  // Debug logging
  console.log('ReviewerDashboard State:', { loading, stats, error, executiveOrders });

  useEffect(() => {
    dispatch(fetchDashboardStats());
    dispatch(fetchExecutiveOrders());
    fetchPMOData();
  }, [dispatch]);
  
  const fetchPMOData = async () => {
    setPmosLoading(true);
    setPmosError("");
    
    try {
      // Fetch EOs assigned to this PMO with their tasks
      const eosResponse = await api.get('/dashboard/pmo/assigned-eos-with-tasks');
      
      if (eosResponse.data.success) {
        setAssignedEOsWithTasks(eosResponse.data.data.executive_orders);
        setAssignedEOs(eosResponse.data.data.executive_orders);
      } else {
        setPmosError('Failed to fetch assigned EOs');
      }
      
      // Fetch team members (executors) under this PMO
      const teamResponse = await api.get('/dashboard/pmo/employees');
      
      if (teamResponse.data.success) {
        setTeamMembers(teamResponse.data.data.employees);
      } else {
        console.warn('Failed to fetch team members');
      }
      
    } catch (err) {
      console.error('Error fetching PMO data:', err);
      setPmosError(err.response?.data?.detail || 'Failed to fetch PMO data');
    } finally {
      setPmosLoading(false);
    }
  };

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
                 Assigned EOs
               </Typography>
               <Typography variant="h4" color="primary.main">
                 {pmosLoading ? '...' : assignedEOs.length}
               </Typography>
               {pmosLoading && (
                 <Typography variant="caption" color="text.secondary">
                   Loading EOs...
                 </Typography>
               )}
             </CardContent>
           </Card>
           <Card sx={{ minWidth: 200, flex: 1 }}>
             <CardContent sx={{ textAlign: 'center' }}>
               <Typography color="text.secondary" gutterBottom>
                 Executors with Tasks
               </Typography>
               <Typography variant="h4" color="info.main">
                 {pmosLoading ? '...' : teamMembers.length}
               </Typography>
               {pmosLoading && (
                 <Typography variant="caption" color="text.secondary">
                   Loading executors...
                 </Typography>
               )}
             </CardContent>
           </Card>
           <Card sx={{ minWidth: 200, flex: 1 }}>
             <CardContent sx={{ textAlign: 'center' }}>
               <Typography color="text.secondary" gutterBottom>
                 Active Tasks
               </Typography>
               <Typography variant="h4" color="secondary.main">
                 {pmosLoading ? '...' : 
                   assignedEOsWithTasks.reduce((total, eo) => total + (eo.tasks?.length || 0), 0)
                 }
               </Typography>
               {pmosLoading && (
                 <Typography variant="caption" color="text.secondary">
                   Loading tasks...
                 </Typography>
               )}
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

             {/* Executive Order Assignment Status */}
       {!pmosLoading && assignedEOsWithTasks.length > 0 && (
         <Card sx={{ borderRadius: 3, mb: 3, bgcolor: 'primary.50', border: '2px solid', borderColor: 'primary.main' }}>
           <CardContent sx={{ textAlign: 'center', py: 3 }}>
             <BusinessIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
             <Typography variant="h5" fontWeight={700} color="primary.main" gutterBottom>
               You are assigned to manage:
             </Typography>
             <Typography variant="h4" fontWeight={600} color="primary.main" sx={{ mb: 1 }}>
               {truncateTitle(assignedEOsWithTasks[0]?.title || 'Executive Order')}
             </Typography>
             {assignedEOsWithTasks[0]?.title && assignedEOsWithTasks[0].title.length > 60 && (
               <Button
                 size="small"
                 variant="text"
                 color="primary"
                 onClick={() => handleViewFullEO(assignedEOsWithTasks[0])}
                 sx={{ mb: 2 }}
               >
                 View Full EO
               </Button>
             )}
             <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
               {assignedEOsWithTasks[0]?.description ? 
                 truncateTitle(assignedEOsWithTasks[0].description, 100) : 
                 'Executive Order Management'
               }
             </Typography>
             <Stack direction="row" spacing={2} justifyContent="center" alignItems="center">
               <Chip 
                 label={`${assignedEOsWithTasks.length} EOs`} 
                 size="large" 
                 color="primary" 
                 icon={<BusinessIcon />}
               />
               <Chip 
                 label={`${assignedEOsWithTasks.reduce((total, eo) => total + (eo.tasks?.length || 0), 0)} Tasks`} 
                 size="large" 
                 color="secondary" 
                 icon={<TaskIcon />}
               />
               <Chip 
                 label={`${teamMembers.length} Executors`} 
                 size="large" 
                 color="info" 
                 icon={<PeopleIcon />}
               />
             </Stack>
             {assignedEOsWithTasks[0]?.pmo_assignment && (
               <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                 Assigned on: {new Date(assignedEOsWithTasks[0].pmo_assignment.assigned_at).toLocaleDateString()}
               </Typography>
             )}
           </CardContent>
         </Card>
       )}

               {/* Team Overview */}
        <SectionHeader
          title="Executors with Tasks"
          subtitle="Executors who have tasks from your assigned Executive Orders"
        />
       
        <Card sx={{ borderRadius: 3, mb: 3 }}>
          <CardContent>
            {pmosLoading ? (
              <Box sx={{ textAlign: 'center', py: 3 }}>
                <Typography>Loading executors...</Typography>
              </Box>
            ) : teamMembers.length > 0 ? (
              <Stack spacing={2}>
                {teamMembers.map((executor) => (
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
                          {executor.org_role || 'Executor'}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {executor.email}
                        </Typography>
                        <Typography variant="caption" color="primary.main" sx={{ display: 'block', mt: 0.5 }}>
                          {executor.assigned_tasks_count || 0} tasks assigned
                        </Typography>
                      </Box>
                    </Box>
                    
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip 
                        label={`${executor.assigned_tasks_count || 0} Tasks`} 
                        size="small" 
                        color="primary" 
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
            ) : (
              <Box sx={{ textAlign: 'center', py: 3 }}>
                <Typography color="text.secondary">
                  No executors with tasks from your assigned EOs yet.
                </Typography>
              </Box>
            )}
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
