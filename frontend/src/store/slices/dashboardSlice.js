import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

export const fetchExecutiveOrders = createAsyncThunk(
  'dashboard/fetchExecutiveOrders',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/dashboard/executive-orders');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch executive orders');
    }
  }
);

export const fetchExecutiveOrderDetails = createAsyncThunk(
  'dashboard/fetchExecutiveOrderDetails',
  async (eoId, { rejectWithValue }) => {
    try {
      const response = await api.get(`/dashboard/executive-orders/${eoId}`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch executive order details');
    }
  }
);

export const fetchDashboardStats = createAsyncThunk(
  'dashboard/fetchDashboardStats',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/dashboard/stats');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch dashboard stats');
    }
  }
);

export const fetchEmailLogs = createAsyncThunk(
  'dashboard/fetchEmailLogs',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/dashboard/email-logs');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch email logs');
    }
  }
);

const initialState = {
  executiveOrders: [],
  selectedEO: null,
  stats: null,
  emailLogs: [],
  loading: false,
  error: null,
};

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearSelectedEO: (state) => {
      state.selectedEO = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchExecutiveOrders.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboardStats.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchEmailLogs.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchExecutiveOrders.fulfilled, (state, action) => {
        state.loading = false;
        // Extract data from the API response structure {success, message, data}
        const orders = action.payload?.data?.executive_orders || action.payload?.executive_orders || [];
        state.executiveOrders = Array.isArray(orders) ? orders : [];
        state.error = null;
      })
      .addCase(fetchExecutiveOrders.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchExecutiveOrderDetails.fulfilled, (state, action) => {
        // Extract data from the API response structure {success, message, data}
        state.selectedEO = action.payload?.data || action.payload;
        state.error = null;
      })
      .addCase(fetchDashboardStats.fulfilled, (state, action) => {
        // Extract data from the API response structure {success, message, data}
        state.stats = action.payload?.data || action.payload;
        state.error = null;
        state.loading = false;
      })
      .addCase(fetchEmailLogs.fulfilled, (state, action) => {
        // Extract data from the API response structure {success, message, data}
        const logs = action.payload?.data?.email_logs || action.payload?.email_logs || [];
        state.emailLogs = Array.isArray(logs) ? logs : [];
        state.error = null;
        state.loading = false;
      });
  },
});

export const { clearError, clearSelectedEO } = dashboardSlice.actions;
export default dashboardSlice.reducer;
