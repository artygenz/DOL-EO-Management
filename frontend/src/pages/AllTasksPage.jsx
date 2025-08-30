import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  Stack, Card, CardContent, Typography, Button, Chip, Alert,
  Box, Divider
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import SectionHeader from "../ui/SectionHeader";
import { fetchAllTasks } from '../store/slices/taskSlice';
import { useAuth } from '../hooks/useAuth';

export default function AllTasksPage() {
  const dispatch = useDispatch();
  const { user } = useAuth();
  const { allTasks, loading, error } = useSelector((state) => state.task);

  useEffect(() => {
    dispatch(fetchAllTasks());
  }, [dispatch]);

  // Debug logging
  console.log('AllTasksPage State:', { allTasks, loading, error });

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <>
      {/* Welcome Header */}
      <Box sx={{ textAlign: 'center', py: 2, mb: 3 }}>
        <Typography variant="h4" fontWeight={700} color="primary.main">
          Your Tasks
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
          Overview of tasks assigned to you
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error: {typeof error === 'string' ? error : error?.detail || error?.message || 'An error occurred'}
        </Alert>
      )}
      
      <SectionHeader
        title="Your Tasks"
        subtitle="Tasks assigned to you"
      />
      
      {allTasks && allTasks.length > 0 ? (
        <Stack spacing={2}>
          {allTasks.filter(task => task && typeof task === 'object').map((task) => (
            <Card key={task.id || Math.random()} sx={{ borderRadius: 3 }}>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="h6" fontWeight={600}>
                      {typeof task.title === 'string' ? task.title : 'Untitled Task'}
                    </Typography>
                    <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                      {typeof task.description === 'string' ? task.description : 'No description available'}
                    </Typography>
                    
                    <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                      {task.due_date && (
                        <Typography variant="body2" color="text.secondary">
                          📅 Due: {new Date(task.due_date).toLocaleDateString()}
                        </Typography>
                      )}
                      {task.category && (
                        <Typography variant="body2" color="text.secondary">
                          🏷️ Category: {task.category}
                        </Typography>
                      )}

                    </Stack>
                  </Box>
                  
                  <Stack spacing={1} alignItems="flex-end">
                    <Chip 
                      label={typeof task.status === 'string' ? task.status : 'Unknown'} 
                      size="small" 
                      color={task.status === 'completed' ? 'success' : task.status === 'in_progress' ? 'warning' : 'default'}
                    />
                  </Stack>
                </Stack>

                <Divider sx={{ my: 2 }} />

                <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }} alignItems="center">
                  <Button component={RouterLink} to={`/tasks/${task.id}`} size="small" variant="outlined">
                    View Details
                  </Button>
                  
                  {task.executive_order && (
                    <Button 
                      component={RouterLink} 
                      to={`/eos/${task.executive_order.id}`} 
                      size="small" 
                      variant="outlined"
                      color="secondary"
                    >
                      View EO
                    </Button>
                  )}
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>
      ) : (
        <Card>
          <CardContent>
            <Typography color="text.secondary">
              {loading ? 'Loading tasks...' : 'No tasks found or you may not have permission to view all tasks.'}
            </Typography>
          </CardContent>
        </Card>
      )}
    </>
  );
}
