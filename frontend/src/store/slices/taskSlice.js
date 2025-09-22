import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

export const fetchUserTasks = createAsyncThunk(
  'task/fetchUserTasks',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/dashboard/tasks');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch tasks');
    }
  }
);

export const fetchAllTasks = createAsyncThunk(
  'task/fetchAllTasks',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/dashboard/tasks');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch all tasks');
    }
  }
);

export const fetchTaskDetails = createAsyncThunk(
  'task/fetchTaskDetails',
  async (taskId, { rejectWithValue }) => {
    try {
      const response = await api.get(`/dashboard/tasks/${taskId}`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch task details');
    }
  }
);

export const updateTaskStatus = createAsyncThunk(
  'task/updateTaskStatus',
  async ({ taskId, status, remarks }, { rejectWithValue }) => {
    try {
      const response = await api.patch(`/dashboard/tasks/${taskId}`, {
        status,
        remarks,
      });
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to update task');
    }
  }
);

export const submitDailyUpdate = createAsyncThunk(
  'task/submitDailyUpdate',
  async (dailyUpdateData, { rejectWithValue }) => {
    try {
      const response = await api.post('/dashboard/employee/daily-update', dailyUpdateData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to submit daily update');
    }
  }
);

export const assignTaskToResource = createAsyncThunk(
  'task/assignTaskToResource',
  async ({ taskId, assigneeId }, { rejectWithValue }) => {
    try {
      const response = await api.put(`/dashboard/pmo/tasks/${taskId}/assignee`, {
        assignee_id: assigneeId
      });
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to assign task');
    }
  }
);

// New async thunks for daily updates
export const fetchEmployeeDailyUpdates = createAsyncThunk(
  'task/fetchEmployeeDailyUpdates',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/dashboard/employee/my-updates');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch daily updates');
    }
  }
);

export const fetchPMODailyUpdates = createAsyncThunk(
  'task/fetchPMODailyUpdates',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/dashboard/pmo/daily-updates');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch PMO daily updates');
    }
  }
);

const initialState = {
  tasks: [],
  allTasks: [],
  selectedTask: null,
  dailyUpdates: [],
  pmoDailyUpdates: [],
  loading: false,
  dailyUpdatesLoading: false,
  pmoDailyUpdatesLoading: false,
  error: null,
  dailyUpdatesError: null,
  pmoDailyUpdatesError: null,
};

const taskSlice = createSlice({
  name: 'task',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearSelectedTask: (state) => {
      state.selectedTask = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchUserTasks.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchUserTasks.fulfilled, (state, action) => {
        state.loading = false;
        // Extract data from the API response structure {success, message, data}
        const taskList = action.payload?.data?.tasks || action.payload?.tasks || [];
        state.tasks = Array.isArray(taskList) ? taskList : [];
        state.error = null;
      })
      .addCase(fetchUserTasks.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchAllTasks.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAllTasks.fulfilled, (state, action) => {
        state.loading = false;
        // Extract data from the API response structure {success, message, data}
        const allTaskList = action.payload?.data?.tasks || action.payload?.tasks || [];
        state.allTasks = Array.isArray(allTaskList) ? allTaskList : [];
        state.error = null;
      })
      .addCase(fetchAllTasks.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchTaskDetails.fulfilled, (state, action) => {
        // Extract data from the API response structure {success, message, data}
        state.selectedTask = action.payload?.data || action.payload;
        state.error = null;
      })
      .addCase(updateTaskStatus.fulfilled, (state, action) => {
        // Extract data from the API response structure {success, message, data}
        const updatedTask = action.payload?.data || action.payload;
        state.tasks = state.tasks.map(task =>
          task.id === updatedTask.id ? updatedTask : task
        );
        if (state.selectedTask?.id === updatedTask.id) {
          state.selectedTask = updatedTask;
        }
        state.error = null;
      })
      .addCase(submitDailyUpdate.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(submitDailyUpdate.fulfilled, (state, action) => {
        state.loading = false;
        // Extract data from the API response structure {success, message, data}
        const newUpdate = action.payload?.data || action.payload;
        if (newUpdate) {
          state.dailyUpdates.push(newUpdate);
        }
        state.error = null;
      })
      .addCase(submitDailyUpdate.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(assignTaskToResource.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(assignTaskToResource.fulfilled, (state, action) => {
        state.loading = false;
        // Extract data from the API response structure {success, message, data}
        const updatedTask = action.payload?.data || action.payload;
        // Update the task in both tasks and allTasks arrays
        state.tasks = state.tasks.map(task =>
          task.id === updatedTask.task_id ? { ...task, assignee_id: updatedTask.new_assignee_id } : task
        );
        state.allTasks = state.allTasks.map(task =>
          task.id === updatedTask.task_id ? { ...task, assignee_id: updatedTask.new_assignee_id } : task
        );
        state.error = null;
      })
      .addCase(assignTaskToResource.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // New daily update reducers
      .addCase(fetchEmployeeDailyUpdates.pending, (state) => {
        state.dailyUpdatesLoading = true;
        state.dailyUpdatesError = null;
      })
      .addCase(fetchEmployeeDailyUpdates.fulfilled, (state, action) => {
        state.dailyUpdatesLoading = false;
        const updatesList = action.payload?.data?.updates || action.payload?.updates || [];
        state.dailyUpdates = Array.isArray(updatesList) ? updatesList : [];
        state.dailyUpdatesError = null;
      })
      .addCase(fetchEmployeeDailyUpdates.rejected, (state, action) => {
        state.dailyUpdatesLoading = false;
        state.dailyUpdatesError = action.payload;
      })
      .addCase(fetchPMODailyUpdates.pending, (state) => {
        state.pmoDailyUpdatesLoading = true;
        state.pmoDailyUpdatesError = null;
      })
      .addCase(fetchPMODailyUpdates.fulfilled, (state, action) => {
        state.pmoDailyUpdatesLoading = false;
        const updatesList = action.payload?.data?.daily_updates || action.payload?.daily_updates || [];
        state.pmoDailyUpdates = Array.isArray(updatesList) ? updatesList : [];
        state.pmoDailyUpdatesError = null;
      })
      .addCase(fetchPMODailyUpdates.rejected, (state, action) => {
        state.pmoDailyUpdatesLoading = false;
        state.pmoDailyUpdatesError = action.payload;
      });
  },
});

export const { clearError, clearSelectedTask } = taskSlice.actions;
export default taskSlice.reducer;
