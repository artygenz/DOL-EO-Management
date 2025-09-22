import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Stack,
  Button,
  Box,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip
} from '@mui/material';
import AssignmentIndIcon from '@mui/icons-material/AssignmentInd';
import RefreshIcon from '@mui/icons-material/Refresh';
import PersonIcon from '@mui/icons-material/Person';
import BusinessIcon from '@mui/icons-material/Business';
import api from '../services/api';
import { formatDateUSA } from '../utils/dateUtils';

export default function TaskAssignmentManager({ 
  assignedEOsWithTasks, 
  teamMembers, 
  loading, 
  onRefresh,
  onTaskAssigned 
}) {
  const [unassignedTasks, setUnassignedTasks] = useState([]);
  const [assignmentDialogOpen, setAssignmentDialogOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedAssignee, setSelectedAssignee] = useState('');
  const [assigningTask, setAssigningTask] = useState(false);
  const [assignmentError, setAssignmentError] = useState('');

  useEffect(() => {
    // Extract unassigned tasks from assigned EOs
    const extractUnassignedTasks = () => {
      const unassigned = [];
      assignedEOsWithTasks.forEach(eo => {
        if (eo.tasks) {
          eo.tasks.forEach(task => {
            if (!task.assignee) {
              unassigned.push({
                ...task,
                executive_order: {
                  id: eo.id,
                  title: eo.title
                }
              });
            }
          });
        }
      });
      setUnassignedTasks(unassigned);
    };

    extractUnassignedTasks();
  }, [assignedEOsWithTasks]);

  const handleTaskAssignment = (task) => {
    setSelectedTask(task);
    setSelectedAssignee('');
    setAssignmentError('');
    setAssignmentDialogOpen(true);
  };

  const handleAssignTask = async () => {
    if (!selectedAssignee || !selectedTask) return;

    setAssigningTask(true);
    setAssignmentError('');

    try {
      const response = await api.put(`/dashboard/pmo/tasks/${selectedTask.id}/assignee`, {
        assignee_id: selectedAssignee
      });

      if (response.data.success) {
        // Close dialog and refresh data
        setAssignmentDialogOpen(false);
        setSelectedTask(null);
        setSelectedAssignee('');
        
        // Notify parent component to refresh data
        if (onTaskAssigned) {
          onTaskAssigned();
        }
        
        // Show success message (you can add a snackbar here)
        console.log('Task assigned successfully!');
      }
    } catch (error) {
      console.error('Failed to assign task:', error);
      setAssignmentError(error.response?.data?.detail || 'Failed to assign task');
    } finally {
      setAssigningTask(false);
    }
  };

  const closeDialog = () => {
    setAssignmentDialogOpen(false);
    setSelectedTask(null);
    setSelectedAssignee('');
    setAssignmentError('');
  };

  const getTaskPriorityColor = (category) => {
    if (category?.includes('Director')) return 'primary';
    if (category?.includes('Lead')) return 'secondary';
    return 'default';
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress size={40} />
      </Box>
    );
  }

  return (
    <>
      {/* Unassigned Tasks Section */}
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
            <Box>
              <Typography variant="h6" fontWeight={700} gutterBottom>
                🎯 Unassigned Tasks
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {unassignedTasks.length} task{unassignedTasks.length !== 1 ? 's' : ''} need{unassignedTasks.length !== 1 ? '' : 's'} assignment
              </Typography>
            </Box>
            <Button
              size="small"
              variant="outlined"
              onClick={onRefresh}
              disabled={loading}
              startIcon={<RefreshIcon />}
            >
              Refresh
            </Button>
          </Stack>

          {unassignedTasks.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <BusinessIcon sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
              <Typography variant="h6" color="success.main" gutterBottom>
                All Tasks Assigned! 🎉
              </Typography>
              <Typography color="text.secondary">
                Great job! All tasks are currently assigned to team members.
              </Typography>
            </Box>
          ) : (
            <Stack spacing={2}>
              {unassignedTasks.map((task) => (
                <Card key={task.id} variant="outlined" sx={{ borderRadius: 2 }}>
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                      <Box sx={{ flex: 1 }}>
                        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                          <Typography variant="h6" fontWeight={600}>
                            {task.title}
                          </Typography>
                          {task.category && (
                            <Chip 
                              label={task.category} 
                              size="small" 
                              color={getTaskPriorityColor(task.category)}
                              variant="outlined"
                            />
                          )}
                        </Stack>
                        
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {task.description || 'No description available'}
                        </Typography>
                        
                        <Stack direction="row" spacing={2} alignItems="center">
                          {task.executive_order && (
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <BusinessIcon fontSize="small" color="action" />
                              <Typography variant="body2" color="text.secondary">
                                {task.executive_order.title}
                              </Typography>
                            </Box>
                          )}
                          
                          {task.due_date && (
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <Typography variant="body2" color="text.secondary">
                                📅 Due: {formatDateUSA(task.due_date)}
                              </Typography>
                            </Box>
                          )}
                        </Stack>
                      </Box>
                      
                      <Button
                        variant="contained"
                        size="medium"
                        onClick={() => handleTaskAssignment(task)}
                        startIcon={<AssignmentIndIcon />}
                        sx={{ minWidth: 140 }}
                      >
                        Assign Task
                      </Button>
                    </Stack>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>

      {/* Task Assignment Dialog */}
      <Dialog 
        open={assignmentDialogOpen} 
        onClose={closeDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Stack direction="row" spacing={1} alignItems="center">
            <AssignmentIndIcon color="primary" />
            <Typography variant="h6">
              Assign Task to Team Member
            </Typography>
          </Stack>
        </DialogTitle>
        
        <DialogContent>
          {selectedTask && (
            <Stack spacing={3}>
              {/* Task Details */}
              <Box>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Task Details
                </Typography>
                <Card variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
                  <Typography variant="h6" color="primary.main" sx={{ mb: 1 }}>
                    {selectedTask.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {selectedTask.description || 'No description available'}
                  </Typography>
                  
                  <Stack direction="row" spacing={2} alignItems="center" sx={{ mt: 2 }}>
                    {selectedTask.executive_order && (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <BusinessIcon fontSize="small" color="action" />
                        <Typography variant="body2" color="text.secondary">
                          EO: {selectedTask.executive_order.title}
                        </Typography>
                      </Box>
                    )}
                    
                    {selectedTask.category && (
                      <Chip 
                        label={selectedTask.category} 
                        size="small" 
                        color={getTaskPriorityColor(selectedTask.category)}
                      />
                    )}
                  </Stack>
                </Card>
              </Box>

              <Divider />

              {/* Team Member Selection */}
              <Box>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Select Team Member
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Choose a team member to assign this task to:
                </Typography>
                
                <FormControl fullWidth>
                  <InputLabel>Assign to</InputLabel>
                  <Select
                    value={selectedAssignee}
                    onChange={(e) => setSelectedAssignee(e.target.value)}
                    label="Assign to"
                  >
                    {teamMembers.map((member) => (
                      <MenuItem key={member.id} value={member.id}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <PersonIcon fontSize="small" color="action" />
                          <Box>
                            <Typography variant="body1" fontWeight={500}>
                              {member.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {member.org_role || 'Resource'}
                            </Typography>
                          </Box>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                
                {selectedAssignee && (
                  <Card variant="outlined" sx={{ mt: 2, p: 2, bgcolor: 'success.50', borderColor: 'success.200' }}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <PersonIcon color="success" />
                      <Typography variant="body2" color="success.dark">
                        This task will be assigned to: <strong>{teamMembers.find(m => m.id === selectedAssignee)?.name}</strong>
                      </Typography>
                    </Stack>
                  </Card>
                )}
              </Box>

              {/* Error Display */}
              {assignmentError && (
                <Alert severity="error">
                  {assignmentError}
                </Alert>
              )}
            </Stack>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={closeDialog} disabled={assigningTask}>
            Cancel
          </Button>
          <Button 
            onClick={handleAssignTask}
            variant="contained"
            disabled={!selectedAssignee || assigningTask}
            startIcon={assigningTask ? <CircularProgress size={16} /> : <AssignmentIndIcon />}
          >
            {assigningTask ? 'Assigning...' : 'Assign Task'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
