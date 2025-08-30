import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  Typography,
  Stack,
  Button,
  Box,
  Alert,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  CircularProgress
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import api from "../services/api";
import SectionHeader from "../ui/SectionHeader";
import AssignmentIndIcon from "@mui/icons-material/AssignmentInd";
import HistoryIcon from "@mui/icons-material/History";

export default function ExecutorDashboard() {
  const { user } = useAuth();

  // Tasks state
  const [assignedTasks, setAssignedTasks] = useState([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [tasksError, setTasksError] = useState("");

  // Daily update form state
  const [selectedTask, setSelectedTask] = useState("");
  const [updateText, setUpdateText] = useState("");
  const [progressPct, setProgressPct] = useState(0);
  const [hoursSpent, setHoursSpent] = useState("");
  const [statusNote, setStatusNote] = useState("");
  const [blockers, setBlockers] = useState("");
  const [nextActions, setNextActions] = useState("");
  const [todayUpdateSubmitted, setTodayUpdateSubmitted] = useState(false);
  const [submittingUpdate, setSubmittingUpdate] = useState(false);

  // Daily updates history state
  const [dailyUpdates, setDailyUpdates] = useState([]);
  const [dailyUpdatesLoading, setDailyUpdatesLoading] = useState(false);
  const [dailyUpdatesError, setDailyUpdatesError] = useState("");

  useEffect(() => {
    fetchExecutorData();
    fetchDailyUpdatesHistory();
    checkTodayUpdateStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchExecutorData = async () => {
    setTasksLoading(true);
    setTasksError("");

    try {
      // Fetch tasks assigned to this executor (all statuses)
      const tasksResponse = await api.get("/dashboard/tasks");

      if (tasksResponse.data?.success) {
        setAssignedTasks(tasksResponse.data.data.tasks || []);
      } else {
        setTasksError("Failed to fetch assigned tasks");
      }
    } catch (err) {
      console.error("Error fetching executor data:", err);
      setTasksError(err?.response?.data?.detail || "Failed to fetch assigned tasks");
    } finally {
      setTasksLoading(false);
    }
  };

  const fetchDailyUpdatesHistory = async () => {
    setDailyUpdatesLoading(true);
    setDailyUpdatesError("");

    try {
      // GET history
      const response = await api.get("/dashboard/employee/my-updates");
      if (response.data?.success) {
        setDailyUpdates(response.data.data.updates || []);
      } else {
        setDailyUpdatesError("Failed to fetch daily update history");
      }
    } catch (err) {
      console.error("Error fetching daily updates history:", err);
      setDailyUpdatesError(
        err?.response?.data?.detail || "Failed to fetch daily update history"
      );
    } finally {
      setDailyUpdatesLoading(false);
    }
  };

  const checkTodayUpdateStatus = () => {
    const todayKey = new Date().toDateString();
    const flag = localStorage.getItem(`dailyUpdate_${user?.id}_${todayKey}`);
    setTodayUpdateSubmitted(!!flag);
  };

  const handleDailyUpdate = async () => {
    if (!selectedTask || !updateText.trim() || todayUpdateSubmitted) return;

    setSubmittingUpdate(true);

    const payload = {
      task_id: selectedTask,
      update_text: updateText.trim(),
      progress_pct: Number(progressPct) || 0,
      hours_spent: hoursSpent ? parseFloat(hoursSpent) : null,
      status_note: statusNote || null,
      blockers: blockers ? { description: blockers } : null,
      next_actions: nextActions ? { description: nextActions } : null,
    };

    try {
      // NOTE: If your POST endpoint differs, change it here.
      // Some backends use the same path with POST for create:
      // e.g., POST /dashboard/employee/my-updates
      const res = await api.post("/dashboard/employee/daily-update", payload);

      if (res.data?.success) {
        // Reset form
        setSelectedTask("");
        setUpdateText("");
        setProgressPct(0);
        setHoursSpent("");
        setStatusNote("");
        setBlockers("");
        setNextActions("");

        // Mark as submitted today
        const todayKey = new Date().toDateString();
        localStorage.setItem(`dailyUpdate_${user?.id}_${todayKey}`, "true");
        setTodayUpdateSubmitted(true);

        // Refresh lists
        fetchExecutorData();
        fetchDailyUpdatesHistory();
        console.log("Daily update submitted successfully!");
      } else {
        throw new Error(res.data?.detail || "Submit failed");
      }
    } catch (error) {
      console.error("Failed to submit daily update:", error);
      // Optional: show a visible error if you want
    } finally {
      setSubmittingUpdate(false);
    }
  };

  if (tasksLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: 400 }}>
        <CircularProgress size={60} />
      </Box>
    );
  }

  return (
    <Stack spacing={3}>
      {/* Welcome Header */}
      <Box sx={{ textAlign: "center", py: 2 }}>
        <Typography variant="h4" fontWeight={700} color="primary.main">
          Welcome back, {user?.name?.split(" ")[0] || "Team Member"}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
          Here's your task overview and daily update form
        </Typography>
      </Box>

      {/* Error Alert */}
      {tasksError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {tasksError}
        </Alert>
      )}

      {/* Simple Stats Cards (no Redux) */}
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <Card sx={{ minWidth: 200, flex: 1 }}>
          <CardContent sx={{ textAlign: "center" }}>
            <Typography color="text.secondary" gutterBottom>
              Active Tasks
            </Typography>
            <Typography variant="h4" color="primary.main">
              {assignedTasks.length}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ minWidth: 200, flex: 1 }}>
          <CardContent sx={{ textAlign: "center" }}>
            <Typography color="text.secondary" gutterBottom>
              Team Role
            </Typography>
            <Typography variant="h6" sx={{ textTransform: "capitalize" }}>
              {user?.org_role || "Executor"}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ minWidth: 200, flex: 1 }}>
          <CardContent sx={{ textAlign: "center" }}>
            <Typography color="text.secondary" gutterBottom>
              Department
            </Typography>
            <Typography variant="h6" color="secondary.main">
              {(user?.department || "Team") + " Member"}
            </Typography>
          </CardContent>
        </Card>
      </Stack>

      {/* Daily Update Form */}
      <Card sx={{ borderRadius: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={700} gutterBottom>
            📝 {todayUpdateSubmitted ? "Daily Update Submitted" : "Submit Daily Update"}
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            {todayUpdateSubmitted
              ? "Your daily update has been submitted for today. Check back tomorrow for the next update."
              : "Keep your reviewer updated on your progress"}
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
                {assignedTasks.map((task) => (
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
              disabled={
                !selectedTask ||
                !updateText.trim() ||
                todayUpdateSubmitted ||
                submittingUpdate
              }
              sx={{ mt: 2 }}
            >
              {submittingUpdate ? (
                <>
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  Submitting...
                </>
              ) : todayUpdateSubmitted ? (
                "Already Submitted Today"
              ) : (
                "Submit Daily Update"
              )}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Divider />

      {/* Quick Access to Tasks */}
      <SectionHeader title="Quick Access" subtitle="Navigate to your tasks and other sections" />
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={2}>
            <Button component={RouterLink} to="/tasks" variant="contained" startIcon={<AssignmentIndIcon />}>
              View My Tasks ({assignedTasks.length})
            </Button>
            <Button component={RouterLink} to="/eos" variant="outlined">
              View Executive Orders
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Daily Updates History */}
      <SectionHeader
        title="Daily Updates History"
        subtitle="View your submitted daily updates"
        icon={<HistoryIcon />}
      />
      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          {dailyUpdatesLoading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
              <CircularProgress />
            </Box>
          ) : dailyUpdatesError ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {dailyUpdatesError}
            </Alert>
          ) : dailyUpdates.length === 0 ? (
            <Box sx={{ textAlign: "center", py: 3 }}>
              <Typography color="text.secondary">
                No daily updates submitted yet. Submit your first update above!
              </Typography>
            </Box>
          ) : (
            <Stack spacing={2}>
              {dailyUpdates.map((update) => (
                <Card key={update.id} variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="h6" fontWeight={600} color="primary.main" gutterBottom>
                    {update.task?.title || "Task Title Not Available"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Date: {update.date ? new Date(update.date).toLocaleDateString() : "N/A"}
                  </Typography>
                  <Typography variant="body2">Progress: {update.progress_pct ?? 0}%</Typography>
                  <Typography variant="body2">Hours: {update.hours_spent ?? "N/A"}</Typography>
                  <Typography variant="body2">Status: {update.status_note || "N/A"}</Typography>
                  <Typography variant="body2">Notes: {update.notes || "N/A"}</Typography>
                </Card>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
