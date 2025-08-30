import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Stack,
  Chip,
  Button,
  Box,
  Alert,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { fetchUserTasks, submitDailyUpdate } from '../store/slices/taskSlice';
import { useAuth } from '../hooks/useAuth';
import { fetchDashboardStats } from '../store/slices/dashboardSlice';

export default function ExecutorDashboard() {
  const dispatch = useDispatch();
  const { user } = useAuth();
  const { tasks, loading } = useSelector((state) => state.task);
  const { stats } = useSelector((state) => state.dashboard);
  
  // Debug logging
  console.log('ExecutorDashboard State:', { tasks, loading, stats, user });
  
  // Daily update form state
  const [selectedTask, setSelectedTask] = useState("");
  const [updateText, setUpdateText] = useState("");
  const [progressPct, setProgressPct] = useState(0);
  const [hoursSpent, setHoursSpent] = useState("");
  const [statusNote, setStatusNote] = useState("");
  const [blockers, setBlockers] = useState("");
  const [nextActions, setNextActions] = useState("");
  const [todayUpdateSubmitted, setTodayUpdateSubmitted] = useState(false);

  useEffect(() => {
    dispatch(fetchUserTasks());
    dispatch(fetchDashboardStats());
    
    // Check if today's update is already submitted
    checkTodayUpdateStatus();
  }, [dispatch]);

  const checkTodayUpdateStatus = () => {
    const today = new Date().toDateString();
    
    // TODO: Check from backend if daily update exists for today
    // For now, we'll check localStorage as a simple solution
    const lastUpdateDate = localStorage.getItem(`dailyUpdate_${user?.id}_${today}`);
    setTodayUpdateSubmitted(!!lastUpdateDate);
  };

  const handleDailyUpdate = async () => {
    if (!selectedTask || !updateText.trim()) return;
    if (todayUpdateSubmitted) return; // Prevent duplicate submissions
    
    const dailyUpdateData = {
      task_id: selectedTask,
      update_text: updateText,
      progress_pct: progressPct,
      hours_spent: hoursSpent ? parseFloat(hoursSpent) : null,
      status_note: statusNote,
      blockers: blockers ? { description: blockers } : null,
      next_actions: nextActions ? { description: nextActions } : null
    };
    
    const result = await dispatch(submitDailyUpdate(dailyUpdateData));
    
    if (submitDailyUpdate.fulfilled.match(result)) {
      // Reset form
      setSelectedTask("");
      setUpdateText("");
      setProgressPct(0);
      setHoursSpent("");
      setStatusNote("");
      setBlockers("");
      setNextActions("");
      
      // Mark today's update as submitted
      const today = new Date().toDateString();
      localStorage.setItem(`dailyUpdate_${user?.id}_${today}`, 'true');
      setTodayUpdateSubmitted(true);
      
      // Show success message (you can add a snackbar here later)
      console.log('Daily update submitted successfully!');
    }
  };

  const myTasks = tasks.filter((t) => t.assignee_id === user?.id);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <Stack spacing={3}>
      {/* Welcome Header */}
      <Box sx={{ textAlign: 'center', py: 2 }}>
        <Typography variant="h4" fontWeight={700} color="primary.main">
          Welcome back, {user?.name?.split(' ')[0] || 'Team Member'}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
          Here's your task overview and daily update form
        </Typography>
      </Box>

      {/* Stats Cards */}
      {stats && (
        <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography color="text.secondary" gutterBottom>
                Active Tasks
              </Typography>
              <Typography variant="h4" color="primary.main">
                {myTasks.length}
              </Typography>
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography color="text.secondary" gutterBottom>
                Team Role
              </Typography>
              <Typography variant="h6" sx={{ textTransform: 'capitalize' }}>
                {stats.user?.org_role || 'Executor'}
              </Typography>
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography color="text.secondary" gutterBottom>
                Your Team
              </Typography>
              <Typography variant="h6" color="secondary.main">
                {stats.user?.org_role || 'Team'} Member
              </Typography>
            </CardContent>
          </Card>
        </Stack>
      )}

      {/* Daily Update Form */}
      <Card sx={{ borderRadius: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={700} gutterBottom>
            📝 {todayUpdateSubmitted ? 'Daily Update Submitted' : 'Submit Daily Update'}
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            {todayUpdateSubmitted 
              ? 'Your daily update has been submitted for today. Check back tomorrow for the next update.'
              : 'Keep your reviewer updated on your progress'
            }
          </Typography>
          
          {todayUpdateSubmitted && (
            <Alert severity="success" sx={{ mb: 3 }}>
              ✅ Daily update already submitted for today. You can submit another update tomorrow.
            </Alert>
          )}
          
          <Stack spacing={2}>
            <FormControl fullWidth>
              <InputLabel>Select Task</InputLabel>
              <Select
                value={selectedTask}
                onChange={(e) => setSelectedTask(e.target.value)}
                label="Select Task"
                disabled={todayUpdateSubmitted}
              >
                {myTasks.map((task) => (
                  <MenuItem key={task.id} value={task.id}>
                    {task.title}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              fullWidth
              multiline
              rows={3}
              label="What did you work on today?"
              value={updateText}
              onChange={(e) => setUpdateText(e.target.value)}
              placeholder="Describe your progress, achievements, and any challenges..."
              disabled={todayUpdateSubmitted}
            />

            <Stack direction="row" spacing={2}>
              <TextField
                type="number"
                label="Progress %"
                value={progressPct}
                onChange={(e) => setProgressPct(Number(e.target.value))}
                inputProps={{ min: 0, max: 100 }}
                sx={{ width: 150 }}
                disabled={todayUpdateSubmitted}
              />
              <TextField
                type="number"
                label="Hours Spent"
                value={hoursSpent}
                onChange={(e) => setHoursSpent(e.target.value)}
                inputProps={{ min: 0, step: 0.5 }}
                sx={{ width: 150 }}
                disabled={todayUpdateSubmitted}
              />
            </Stack>

            <TextField
              fullWidth
              label="Status Note"
              value={statusNote}
              onChange={(e) => setStatusNote(e.target.value)}
              placeholder="Any important status updates..."
              disabled={todayUpdateSubmitted}
            />

            <TextField
              fullWidth
              label="Blockers/Challenges"
              value={blockers}
              onChange={(e) => setBlockers(e.target.value)}
              placeholder="What's blocking your progress?"
              disabled={todayUpdateSubmitted}
            />

            <TextField
              fullWidth
              label="Next Actions"
              value={nextActions}
              onChange={(e) => setNextActions(e.target.value)}
              placeholder="What will you work on next?"
              disabled={todayUpdateSubmitted}
            />

            <Button
              variant="contained"
              size="large"
              onClick={handleDailyUpdate}
              disabled={!selectedTask || !updateText.trim() || todayUpdateSubmitted}
              sx={{ mt: 2 }}
            >
              {todayUpdateSubmitted ? 'Already Submitted Today' : 'Submit Daily Update'}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Divider />

      {/* Tasks Section */}
      <Box>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          🎯 Active Tasks
        </Typography>
        
        {myTasks.length === 0 ? (
          <Card>
            <CardContent sx={{ textAlign: 'center', py: 4 }}>
              <Typography color="text.secondary">
                No tasks assigned yet. Your reviewer will assign tasks to you.
              </Typography>
            </CardContent>
          </Card>
        ) : (
          <Stack spacing={2}>
            {myTasks.map((task) => (
              <Card key={task.id} sx={{ borderRadius: 3 }}>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="h6" fontWeight={600}>
                        {task.title}
                      </Typography>
                      <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                        {task.description || 'No description available'}
                      </Typography>
                      
                      {task.due_date && (
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          📅 Due: {new Date(task.due_date).toLocaleDateString()}
                        </Typography>
                      )}
                    </Box>
                    
                    <Stack spacing={1} alignItems="flex-end">
                      <Chip 
                        label={task.status} 
                        size="small" 
                        color={task.status === 'completed' ? 'success' : 'primary'}
                      />
                      {task.category && (
                        <Chip 
                          label={task.category} 
                          size="small" 
                          variant="outlined"
                        />
                      )}
                    </Stack>
                  </Stack>

                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Progress: {task.progress_pct || 0}%
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={task.progress_pct || 0}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </Box>

                  <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
                    <Button
                      component={RouterLink}
                      to={`/task/${task.id}`}
                      size="small"
                      variant="outlined"
                    >
                      View Details
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => setSelectedTask(task.id)}
                    >
                      Update Progress
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>
        )}
      </Box>
    </Stack>
  );
}
