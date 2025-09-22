import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  Stack,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Alert,
  Box,
  FormControl,
  InputLabel,
  Select,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider,
  Avatar,
  MenuItem,
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import AssignmentIndIcon from "@mui/icons-material/AssignmentInd";
import PeopleIcon from "@mui/icons-material/People";
import TaskIcon from "@mui/icons-material/Task";
import BusinessIcon from "@mui/icons-material/Business";
import SectionHeader from "../ui/SectionHeader";
import { fetchDashboardStats, fetchExecutiveOrders } from "../store/slices/dashboardSlice";
import { assignTaskToResource } from "../store/slices/taskSlice";
import { useAuth } from "../hooks/useAuth";
import api from "../services/api";
import { formatDateUSA } from "../utils/dateUtils";

export default function PMODashboard() {
  const dispatch = useDispatch();
  const { user } = useAuth();
  const { loading, stats, error, executiveOrders } = useSelector((state) => state.dashboard);

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

  // Task details dialog state (NEW)
  const [taskDetailsDialogOpen, setTaskDetailsDialogOpen] = useState(false);
  const [selectedTaskForDetails, setSelectedTaskForDetails] = useState(null);
  const [taskProgressLoading, setTaskProgressLoading] = useState(false);
  const [taskProgress, setTaskProgress] = useState([]);
  const [taskProgressError, setTaskProgressError] = useState("");

  // Debug logging
  console.log("PMODashboard State:", { loading, stats, error, executiveOrders });

  useEffect(() => {
    dispatch(fetchDashboardStats());
    dispatch(fetchExecutiveOrders());
    fetchPMOData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch]);

  const fetchPMOData = async () => {
    setPmosLoading(true);
    setPmosError("");

    try {
      // Fetch EOs assigned to this PMO with their tasks
      const eosResponse = await api.get("/dashboard/pmo/assigned-eos-with-tasks");

      if (eosResponse.data.success) {
        setAssignedEOsWithTasks(eosResponse.data.data.executive_orders);
        setAssignedEOs(eosResponse.data.data.executive_orders);
      } else {
        setPmosError("Failed to fetch assigned EOs");
      }

      // Fetch team members (resources) under this PMO
      const teamResponse = await api.get("/dashboard/pmo/employees");

      if (teamResponse.data.success) {
        setTeamMembers(teamResponse.data.data.employees);
      } else {
        console.warn("Failed to fetch team members");
      }
    } catch (err) {
      console.error("Error fetching PMO data:", err);
      setPmosError(err.response?.data?.detail || "Failed to fetch PMO data");
    } finally {
      setPmosLoading(false);
    }
  };

  const handleTaskAssignment = (task) => {
    setSelectedTask(task);
    setSelectedAssignee(task.assignee_id || "");
    setAssignmentDialogOpen(true);
  };

  const handleTaskAssignmentToResource = async () => {
    if (!selectedAssignee) return;

    setAssigningTask(true);

    try {
      await dispatch(
        assignTaskToResource({
          taskId: selectedTask.id,
          assigneeId: selectedAssignee,
        })
      ).unwrap();

      console.log("✅ Task assigned successfully!");

      setAssignmentDialogOpen(false);
      dispatch(fetchExecutiveOrders());
    } catch (error) {
      console.error("Failed to assign task:", error);
    } finally {
      setAssigningTask(false);
    }
  };

  const getAvailableResources = () => {
    // Use dynamic data from backend
    return teamMembers.map((e) => ({
      id: e.id,
      name: e.name,
      role: e.org_role || "Resource",
      email: e.email,
    }));
  };

  const getTaskStatusColor = (status) => {
    switch (status) {
      case "completed":
      case "approved":
        return "success";
      case "in_progress":
        return "warning";
      case "rejected":
        return "error";
      default:
        return "default";
    }
  };

  const formatTaskStatus = (status) => {
    switch (status) {
      case "completed": return "Completed";
      case "in_progress": return "In Progress";
      case "approved": return "Approved";
      case "rejected": return "Rejected";
      case "pending": return "Pending";
      default: return status;
    }
  };

  const truncateTitle = (title, maxLength = 60) => {
    if (!title) return "";
    return title.length <= maxLength ? title : `${title.substring(0, maxLength)}...`;
  };

  const handleViewFullEO = (eo) => {
    setSelectedEoForDetails(eo);
    setEoDetailsDialogOpen(true);
  };

  // ---- Task Details (NEW) ----
  const handleTaskDetailsOpen = async (task) => {
    setSelectedTaskForDetails(task);
    setTaskProgress([]);
    setTaskProgressError("");
    setTaskDetailsDialogOpen(true);
    await fetchTaskProgress(task.id);
  };

  const handleTaskDetailsClose = () => {
    setTaskDetailsDialogOpen(false);
    setSelectedTaskForDetails(null);
    setTaskProgress([]);
    setTaskProgressError("");
  };

  const fetchTaskProgress = async (taskId) => {
    setTaskProgressLoading(true);
    setTaskProgressError("");
    try {
      // Adjust endpoint to your backend contract if different
      const response = await api.get(`/dashboard/pmo/daily-updates?task_id=${taskId}`);
      if (response.data?.success) {
        setTaskProgress(response.data.data.daily_updates || []);
      } else {
        setTaskProgress([]);
        setTaskProgressError("Failed to load progress updates.");
      }
    } catch (err) {
      console.error("Error fetching task progress:", err);
      setTaskProgress([]);
      setTaskProgressError(err.response?.data?.detail || "Failed to load progress updates.");
    } finally {
      setTaskProgressLoading(false);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <>
      {/* Welcome Header */}
      <Box sx={{ textAlign: "center", py: 2, mb: 3 }}>
        <Typography variant="h4" fontWeight={700} color="primary.main">
          Welcome back, {user?.name?.split(" ")[0] || "PMO"}
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
            <CardContent sx={{ textAlign: "center" }}>
              <Typography color="text.secondary" gutterBottom>
                Assigned EOs
              </Typography>
              <Typography variant="h4" color="primary.main">
                {pmosLoading ? "..." : assignedEOs.length}
              </Typography>
              {pmosLoading && (
                <Typography variant="caption" color="text.secondary">
                  Loading EOs...
                </Typography>
              )}
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography color="text.secondary" gutterBottom>
                Resources with Tasks
              </Typography>
              <Typography variant="h4" color="info.main">
                {pmosLoading ? "..." : teamMembers.length}
              </Typography>
              {pmosLoading && (
                <Typography variant="caption" color="text.secondary">
                  Loading resources...
                </Typography>
              )}
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200, flex: 1 }}>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography color="text.secondary" gutterBottom>
                Active Tasks
              </Typography>
              <Typography variant="h4" color="secondary.main">
                {pmosLoading
                  ? "..."
                  : assignedEOsWithTasks.reduce((total, eo) => total + (eo.tasks?.length || 0), 0)}
              </Typography>
              {pmosLoading && (
                <Typography variant="caption" color="text.secondary">
                  Loading tasks...
                </Typography>
              )}
            </CardContent>
          </Card>
        </Stack>
      )}

      {/* Executive Order Assignment Status */}
      {!pmosLoading && assignedEOsWithTasks.length > 0 && (
        <Card sx={{ borderRadius: 3, mb: 3, bgcolor: "primary.50", border: "2px solid", borderColor: "primary.main" }}>
          <CardContent sx={{ textAlign: "center", py: 3 }}>
            <BusinessIcon sx={{ fontSize: 48, color: "primary.main", mb: 2 }} />
            <Typography variant="h5" fontWeight={700} color="primary.main" gutterBottom>
              You are assigned to manage:
            </Typography>
            <Typography variant="h4" fontWeight={600} color="primary.main" sx={{ mb: 1 }}>
              {truncateTitle(assignedEOsWithTasks[0]?.title || "Executive Order")}
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
            <Stack direction="row" spacing={2} justifyContent="center" alignItems="center">
              <Chip label={`${assignedEOsWithTasks.length} EOs`} size="large" color="primary" icon={<BusinessIcon />} />
              <Chip
                label={`${assignedEOsWithTasks.reduce((total, eo) => total + (eo.tasks?.length || 0), 0)} Tasks`}
                size="large"
                color="secondary"
                icon={<TaskIcon />}
              />
              <Chip label={`${teamMembers.length} Resources`} size="large" color="info" icon={<PeopleIcon />} />
            </Stack>
            {assignedEOsWithTasks[0]?.pmo_assignment && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Assigned on: {formatDateUSA(assignedEOsWithTasks[0].pmo_assignment.assigned_at)}
              </Typography>
            )}
          </CardContent>
        </Card>
      )}

      {/* Team Overview */}
      <SectionHeader title="Resources with Tasks" subtitle="Resources who have tasks from your assigned Executive Orders" />

      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          {pmosLoading ? (
            <Box sx={{ textAlign: "center", py: 3 }}>
              <Typography>Loading resources...</Typography>
            </Box>
          ) : teamMembers.length > 0 ? (
            <Stack spacing={2}>
              {teamMembers.map((resource) => (
                <Box
                  key={resource.id}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    p: 2,
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 2,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                    <Avatar sx={{ bgcolor: "primary.main" }}>
                      {resource.name?.split(" ").map((n) => n[0]).join("")}
                    </Avatar>
                    <Box>
                      <Typography variant="subtitle1" fontWeight={600}>
                        {resource.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {resource.org_role || "Resource"}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {resource.email}
                      </Typography>
                      <Typography variant="caption" color="primary.main" sx={{ display: "block", mt: 0.5 }}>
                        {resource.assigned_tasks_count || 0} tasks assigned
                      </Typography>
                    </Box>
                  </Box>

                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Chip
                      label={`${resource.assigned_tasks_count || 0} Tasks`}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                    <Button component={RouterLink} to={`/tasks?assignee=${resource.id}`} size="small" variant="outlined">
                      View Tasks
                    </Button>
                  </Box>
                </Box>
              ))}
            </Stack>
          ) : (
            <Box sx={{ textAlign: "center", py: 3 }}>
              <Typography color="text.secondary">No resources with tasks from your assigned EOs yet.</Typography>
            </Box>
          )}
        </CardContent>
      </Card>


      {/* Task Management Section */}
      <SectionHeader title="Task Management" subtitle="Assign and manage tasks for your team" />

      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Quick Actions
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Use the navigation buttons above to view and manage tasks, or assign new tasks to your resources.
          </Typography>
          <Stack direction="row" spacing={2}>
            <Button component={RouterLink} to="/tasks" variant="contained" startIcon={<TaskIcon />}>
              View All Tasks
            </Button>
            <Button component={RouterLink} to="/eos" variant="outlined">
              View Executive Orders
            </Button>
          </Stack>
        </CardContent>
      </Card>


      {/* Individual Tasks Section */}
      <SectionHeader title="Individual Tasks" subtitle="View and manage individual tasks assigned to your team" />

      <Card sx={{ borderRadius: 3, mb: 3 }}>
        <CardContent>
          {assignedEOsWithTasks.length === 0 ? (
            <Box sx={{ textAlign: "center", py: 3 }}>
              <Typography color="text.secondary">No tasks found for your assigned Executive Orders.</Typography>
            </Box>
          ) : (
            <Stack spacing={2}>
              {assignedEOsWithTasks.map((eo) => (
                <Box key={eo.id}>
                  <Typography variant="h6" sx={{ mb: 1, color: "primary.main" }}>
                    {eo.title} Tasks:
                  </Typography>
                  {eo.tasks && eo.tasks.length > 0 ? (
                    <Stack spacing={1}>
                      {eo.tasks.map((task) => (
                        <Card key={task.id} variant="outlined" sx={{ p: 2 }}>
                          <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Box sx={{ flex: 1 }}>
                              <Typography variant="subtitle1" fontWeight={500}>
                                {task.title}
                              </Typography>
                              <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5 }}>
                                <Typography variant="body2" color="text.secondary">
                                  Status:
                                </Typography>
                                <Chip size="small" label={formatTaskStatus(task.status)} color={getTaskStatusColor(task.status)} />
                              </Stack>
                              {task.assignee && (
                                <Typography variant="caption" color="text.secondary">
                                  Assigned to: {task.assignee.name} ({task.assignee.email})
                                </Typography>
                              )}
                            </Box>
                            <Stack direction="row" spacing={1}>
                              <Button size="small" onClick={() => handleTaskDetailsOpen(task)} variant="outlined">
                                View Details
                              </Button>
                              <Button size="small" onClick={() => handleTaskAssignment(task)}>
                                {task.assignee ? "Reassign" : "Assign"}
                              </Button>
                            </Stack>
                          </Stack>
                        </Card>
                      ))}
                    </Stack>
                  ) : (
                    <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
                      No tasks for this EO.
                    </Typography>
                  )}
                </Box>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>

      {/* Task Assignment Dialog */}
      <Dialog open={assignmentDialogOpen} onClose={() => setAssignmentDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Stack direction="row" spacing={1} alignItems="center">
            <AssignmentIndIcon color="primary" />
            <Typography variant="h6">Assign Task to Resource</Typography>
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
                  {selectedTask.title || "Untitled Task"}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  ID: {selectedTask.id}
                </Typography>
              </Box>

              <Divider />

              <Box>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Select Resource
                </Typography>
                <FormControl fullWidth>
                  <InputLabel>Assign to</InputLabel>
                  <Select value={selectedAssignee} onChange={(e) => setSelectedAssignee(e.target.value)} label="Assign to">
                    {getAvailableResources().map((resource) => (
                      <MenuItem key={resource.id} value={resource.id}>
                        {resource.name} - {resource.role}
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
            onClick={handleTaskAssignmentToResource}
            variant="contained"
            disabled={!selectedAssignee || assigningTask}
            startIcon={assigningTask ? null : <AssignmentIndIcon />}
          >
            {assigningTask ? "Assigning..." : "Assign Task"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* EO Details Dialog */}
      <Dialog open={eoDetailsDialogOpen} onClose={() => setEoDetailsDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          <Stack direction="row" spacing={1} alignItems="center">
            <BusinessIcon color="primary" />
            <Typography variant="h6">Executive Order Details</Typography>
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
                  {selectedEoForDetails.description || "No description available"}
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
                    color={selectedEoForDetails.status === "processed" ? "success" : "default"}
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
                <Chip label={`${selectedEoForDetails.tasks?.length || 0} Total Tasks`} color="primary" size="medium" />
              </Box>
            </Stack>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setEoDetailsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Task Details Dialog (NEW) */}
      <Dialog open={taskDetailsDialogOpen} onClose={handleTaskDetailsClose} maxWidth="md" fullWidth>
        <DialogTitle>
          <Stack direction="row" spacing={1} alignItems="center">
            <TaskIcon color="primary" />
            <Typography variant="h6">Task Details</Typography>
          </Stack>
        </DialogTitle>

        <DialogContent>
          {selectedTaskForDetails && (
            <Stack spacing={3}>
              <Box>
                <Typography variant="h5" fontWeight={600} gutterBottom>
                  {selectedTaskForDetails.title || "Untitled Task"}
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ mb: 1 }}>
                  ID: {selectedTaskForDetails.id}
                </Typography>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="body1" color="text.secondary">
                    Status:
                  </Typography>
                  <Chip
                    size="small"
                    label={formatTaskStatus(selectedTaskForDetails.status) || "Unknown"}
                    color={getTaskStatusColor(selectedTaskForDetails.status)}
                  />
                </Stack>
                {selectedTaskForDetails.assignee && (
                  <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
                    Assigned To: {selectedTaskForDetails.assignee.name} ({selectedTaskForDetails.assignee.email})
                  </Typography>
                )}
              </Box>

              <Divider />

              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Resource Progress Updates
                </Typography>

                {taskProgressLoading ? (
                  <Typography>Loading progress...</Typography>
                ) : taskProgressError ? (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    {taskProgressError}
                  </Alert>
                ) : taskProgress.length > 0 ? (
                  <Stack spacing={2}>
                    {taskProgress.map((update) => (
                      <Card key={update.id} variant="outlined" sx={{ p: 2 }}>
                        <Stack spacing={1}>
                          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <Typography variant="subtitle2" fontWeight={600}>
                              {update.employee?.name || "Unknown Employee"}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {formatDateUSA(update.created_at)}
                            </Typography>
                          </Box>
                          <Typography variant="body2">Progress: {update.progress_pct ?? 0}%</Typography>
                          <Typography variant="body2">Hours: {update.hours_spent ?? "N/A"}</Typography>
                          <Typography variant="body2">Status: {update.status_note || "N/A"}</Typography>
                          {update.update_text && (
                            <Typography variant="body2" color="text.secondary">
                              Update: {update.update_text}
                            </Typography>
                          )}
                          {update.blockers?.description && (
                            <Typography variant="body2" color="error.main">
                              Blockers: {update.blockers.description}
                            </Typography>
                          )}
                          {update.next_actions?.description && (
                            <Typography variant="body2" color="text.secondary">
                              Next: {update.next_actions.description}
                            </Typography>
                          )}
                        </Stack>
                      </Card>
                    ))}
                  </Stack>
                ) : (
                  <Typography color="text.secondary">No progress updates recorded for this task yet.</Typography>
                )}
              </Box>
            </Stack>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={handleTaskDetailsClose}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
