import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import api from "../../services/api";

export const login = createAsyncThunk(
  "auth/login",
  async ({ email, password }, { rejectWithValue }) => {
    try {
      const res = await api.post("/auth/login", { email, password });
      // FastAPI returns { access_token, user }
      // persist token immediately
      localStorage.setItem("token", res.data.access_token);
      return res.data;
    } catch (err) {
      return rejectWithValue(
        err.response?.data?.detail || "Login failed"
      );
    }
  }
);

export const logout = createAsyncThunk("auth/logout", async () => {
  try {
    await api.post("/auth/logout");
  } catch {
    // ignore API failure, always clear client
  }
  localStorage.removeItem("token");
  return null;
});

export const getCurrentUser = createAsyncThunk(
  "auth/getCurrentUser",
  async (_, { rejectWithValue }) => {
    try {
      const res = await api.get("/auth/me");
      // your backend returns { data: {...} }
      return res.data;
    } catch (err) {
      // If we get a 401, the token is invalid/expired - remove it
      if (err.response?.status === 401) {
        console.log('getCurrentUser: 401 error, removing invalid token');
        localStorage.removeItem('token');
      }
      return rejectWithValue("Failed to get user");
    }
  }
);

const getStoredToken = () => {
  try {
    return localStorage.getItem("token");
  } catch {
    return null;
  }
};

const initialState = {
  user: null,
  token: getStoredToken(),
  isAuthenticated: !!getStoredToken(),
  loading: false,
  // ❌ remove error from redux — keep it local in LoginPage
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setToken: (state, action) => {
      state.token = action.payload;
      state.isAuthenticated = !!action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.loading = true;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload.user;
        state.token = action.payload.access_token;
        state.isAuthenticated = true;
      })
      .addCase(login.rejected, (state) => {
        state.loading = false;
        // do not store error here
      })
      .addCase(logout.fulfilled, (state) => {
        state.user = null;
        state.token = null;
        state.isAuthenticated = false;
        state.loading = false;
      })
      .addCase(getCurrentUser.pending, (state) => {
        state.loading = true;
      })
      .addCase(getCurrentUser.fulfilled, (state, action) => {
        // backend sends { data: {...} }
        state.user = action.payload.data || action.payload.user;
        state.isAuthenticated = true;
        state.loading = false;
      })
      .addCase(getCurrentUser.rejected, (state) => {
        state.user = null;
        state.token = null; // Clear token state on rejection
        state.isAuthenticated = false;
        state.loading = false;
      });
  },
});

export const { setToken } = authSlice.actions;
export default authSlice.reducer;
