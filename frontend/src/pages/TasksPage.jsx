import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Stack, Card, CardContent, Typography, Button, Chip, Alert,
  Box, CircularProgress, Divider
} from '@mui/material';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import AssignmentIndIcon from '@mui/icons-material/AssignmentInd';
import RefreshIcon from '@mui/icons-material/Refresh';
import BusinessIcon from '@mui/icons-material/Business';
import PersonIcon from '@mui/icons-material/Person';
import { useAuth } from '../hooks/useAuth';
import api from '../services/api';
import { formatDateUSA } from '../utils/dateUtils';

export default function TasksPage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const assigneeId = searchParams.get('assignee');
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [assigneeInfo, setAssigneeInfo] = useState(null);

  useEffect(() => {
    fetchTasks();
  }, [user, assigneeId]);

  const fetchTasks = async () => {
    setLoading(true);
    setError("");
    
    try {
      let endpoint = '';
      
      // If we have an assignee ID, fetch tasks for that specific resource
      if (assigneeId) {
        endpoint = `/dashboard/tasks?assignee=${assigneeId}`;
      } else {
        // Choose endpoint based on user role
        if (user?.role === 'admin') {
          endpoint = '/dashboard/cfo/tasks'; // All system tasks
        } else if (user?.role === 'reviewer') {
          endpoint = '/dashboard/pmo/tasks'; // PMO assigned tasks
        } else {
          endpoint = '/dashboard/tasks'; // User's assigned tasks
        }
      }
      
      const response = await api.get(endpoint);
      
      if (response.data.success) {
        setTasks(response.data.data.tasks);
        
        // If we have an assignee ID, also fetch the assignee info
        if (assigneeId && response.data.data.assignee) {
          setAssigneeInfo(response.data.data.assignee);
        }
      } else {
        setError('Failed to fetch tasks');
      }
      
    } catch (err) {
      console.error('Error fetching tasks:', err);
      setError(err.response?.data?.detail || 'Failed to fetch tasks');
    } finally {
      setLoading(false);
    }
  };

  const getTaskStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'in_progress': return 'warning';
      case 'approved': return 'success';
      case 'rejected': return 'error';
      case 'pending': return 'default';
      default: return 'default';
    }
  };

  const formatTaskStatus = (status) => {
    switch (status) {
      case 'completed': return 'Completed';
      case 'in_progress': return 'In Progress';
      case 'approved': return 'Approved';
      case 'rejected': return 'Rejected';
      case 'pending': return 'Pending';
      default: return status;
    }
  };

  const getPageTitle = () => {
    if (assigneeId && assigneeInfo) {
      return `${assigneeInfo.name}'s Tasks`;
    } else if (user?.role === 'admin') {
      return 'All Tasks';
    } else if (user?.role === 'reviewer') {
      return 'PMO Assigned Tasks';
    } else {
      return 'My Assigned Tasks';
    }
  };

  const getPageSubtitle = () => {
    if (assigneeId && assigneeInfo) {
      return `Tasks assigned to ${assigneeInfo.name} (${assigneeInfo.org_role || 'Resource'})`;
    } else if (user?.role === 'admin') {
      return 'View and manage all tasks across the system';
    } else if (user?.role === 'reviewer') {
      return 'Tasks assigned to Executive Orders you manage';
    } else {
      return 'Tasks assigned to you for execution';
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress size={60} />
      </Box>
    );
  }

  return (
    <Stack spacing={3}>
      {/* Page Header */}
      <Box sx={{ textAlign: 'center', py: 2 }}>
        {assigneeId && (
          <Box sx={{ mb: 2 }}>
            <Button
              component={RouterLink}
              to={user?.role === 'reviewer' ? '/dashboard/reviewer' : '/dashboard/admin'}
              variant="outlined"
              size="small"
              startIcon={<PersonIcon />}
            >
              ← Back to Dashboard
            </Button>
          </Box>
        )}
        <Typography variant="h4" fontWeight={700} color="primary.main">
          {getPageTitle()}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
          {getPageSubtitle()}
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Tasks Count Card */}
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent sx={{ textAlign: 'center' }}>
          <Typography variant="h2" fontWeight={700} color="primary.main">
            {tasks.length}
          </Typography>
          <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
            {assigneeId && assigneeInfo 
              ? `${assigneeInfo.name}'s Tasks`
              : user?.role === 'admin' 
                ? 'Total Tasks' 
                : 'Assigned Tasks'
            }
          </Typography>
          {assigneeId && assigneeInfo && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {assigneeInfo.org_role || 'Resource'} • {assigneeInfo.email}
            </Typography>
          )}
          <Button
            size="small"
            variant="outlined"
            onClick={fetchTasks}
            disabled={loading}
            startIcon={<RefreshIcon />}
          >
            Refresh
          </Button>
        </CardContent>
      </Card>

      {/* Tasks List */}
      {tasks.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 4 }}>
            <BusinessIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No Tasks Found
            </Typography>
            <Typography color="text.secondary">
              {user?.role === 'admin' 
                ? 'There are no tasks in the system yet.'
                : 'No tasks have been assigned to you yet.'
              }
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Stack spacing={2}>
          {tasks.map((task) => (
            <Card key={task.id} sx={{ borderRadius: 3 }}>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Box sx={{ flex: 1 }}>
                    <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                      <Typography variant="h6" fontWeight={600}>
                        {task.title}
                      </Typography>
                      <Chip 
                        label={formatTaskStatus(task.status)} 
                        size="small" 
                        color={getTaskStatusColor(task.status)}
                      />
                      {task.category && (
                        <Chip 
                          label={task.category} 
                          size="small" 
                          variant="outlined"
                        />
                      )}
                    </Stack>
                    
                    <Typography color="text.secondary" sx={{ mb: 1 }}>
                      {task.description || 'No description available'}
                    </Typography>
                    
                    <Stack direction="row" spacing={2} alignItems="center" sx={{ mt: 1 }}>
                      {task.executive_order && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <BusinessIcon fontSize="small" color="action" />
                          <Typography variant="body2" color="text.secondary">
                             {task.executive_order.title}
                          </Typography>
                        </Box>
                      )}
                      
                      {task.assignee && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <PersonIcon fontSize="small" color="action" />
                          <Typography variant="body2" color="text.secondary">
                            Assigned to: {task.assignee.name}{task.assignee.org_role ? ` (${task.assignee.org_role})` : ''}
                          </Typography>
                        </Box>
                      )}
                      
                      {task.due_date && (
                        <Typography variant="body2" color="text.secondary">
                          📅 Due: {formatDateUSA(task.due_date)}
                        </Typography>
                      )}
                    </Stack>
                  </Box>
                  
                  <Stack spacing={1} alignItems="flex-end">
                    {user?.role === 'executor' && (
                      <Button
                        size="small"
                        variant="contained"
                        startIcon={<AssignmentIndIcon />}
                        onClick={() => window.location.href = '/dashboard/executor'}
                      >
                        Update Progress
                      </Button>
                    )}
                  </Stack>
                </Stack>

              </CardContent>
            </Card>
          ))}
        </Stack>
      )}
    </Stack>
  );
}
