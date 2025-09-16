import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ChatWindow from '../ChatWindow';
import authSlice from '../../../store/slices/authSlice';

// Mock the API
jest.mock('../../../services/api', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));

// Mock fetch for streaming
global.fetch = jest.fn();

// Create a mock store
const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      auth: authSlice.reducer,
    },
    preloadedState: {
      auth: {
        isAuthenticated: true,
        loading: false,
        user: {
          id: '1',
          name: 'Test User',
          role: 'admin'
        },
        token: 'mock-token',
        ...initialState.auth
      }
    }
  });
};

// Create a mock theme
const theme = createTheme();

const renderWithProviders = (component, { store = createMockStore() } = {}) => {
  return render(
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        {component}
      </ThemeProvider>
    </Provider>
  );
};

describe('ChatWindow', () => {
  beforeEach(() => {
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: jest.fn(() => 'mock-token'),
        setItem: jest.fn(),
        removeItem: jest.fn(),
      },
      writable: true,
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders the chat window', () => {
    renderWithProviders(<ChatWindow onClose={jest.fn()} onNewMessage={jest.fn()} />);
    
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Type your message...')).toBeInTheDocument();
  });

  it('shows role-based greeting for admin user', () => {
    renderWithProviders(<ChatWindow onClose={jest.fn()} onNewMessage={jest.fn()} />);
    
    expect(screen.getByText(/Hello Test User! I'm your AI assistant/)).toBeInTheDocument();
  });

  it('shows role-based greeting for reviewer user', () => {
    const store = createMockStore({
      auth: {
        user: {
          id: '1',
          name: 'Test Reviewer',
          role: 'reviewer'
        }
      }
    });
    
    renderWithProviders(<ChatWindow onClose={jest.fn()} onNewMessage={jest.fn()} />, { store });
    
    expect(screen.getByText(/Hi Test Reviewer! I'm here to help you review tasks/)).toBeInTheDocument();
  });

  it('shows role-based greeting for executor user', () => {
    const store = createMockStore({
      auth: {
        user: {
          id: '1',
          name: 'Test Executor',
          role: 'executor'
        }
      }
    });
    
    renderWithProviders(<ChatWindow onClose={jest.fn()} onNewMessage={jest.fn()} />, { store });
    
    expect(screen.getByText(/Hello Test Executor! I can help you with your tasks/)).toBeInTheDocument();
  });

  it('allows typing in the input field', () => {
    renderWithProviders(<ChatWindow onClose={jest.fn()} onNewMessage={jest.fn()} />);
    
    const input = screen.getByPlaceholderText('Type your message...');
    fireEvent.change(input, { target: { value: 'Hello, AI!' } });
    
    expect(input.value).toBe('Hello, AI!');
  });

  it('sends message when send button is clicked', async () => {
    // Mock successful streaming response
    const mockReader = {
      read: jest.fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"type":"chunk","content":"Hello"}\n\n')
        })
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"type":"chunk","content":" there!"}\n\n')
        })
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"type":"complete","message":"Stream completed"}\n\n')
        })
        .mockResolvedValueOnce({ done: true })
    };

    global.fetch.mockResolvedValueOnce({
      ok: true,
      body: {
        getReader: () => mockReader
      }
    });

    renderWithProviders(<ChatWindow onClose={jest.fn()} onNewMessage={jest.fn()} />);
    
    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    fireEvent.change(input, { target: { value: 'Hello, AI!' } });
    fireEvent.click(sendButton);
    
    // Check that the user message appears
    expect(screen.getByText('Hello, AI!')).toBeInTheDocument();
    
    // Wait for the streaming response
    await waitFor(() => {
      expect(screen.getByText('Hello there!')).toBeInTheDocument();
    });
  });

  it('sends message when Enter key is pressed', () => {
    renderWithProviders(<ChatWindow onClose={jest.fn()} onNewMessage={jest.fn()} />);
    
    const input = screen.getByPlaceholderText('Type your message...');
    fireEvent.change(input, { target: { value: 'Hello, AI!' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter' });
    
    // The message should be sent (we can't easily test the full flow without mocking fetch)
    expect(input.value).toBe(''); // Input should be cleared
  });

  it('does not send empty messages', () => {
    renderWithProviders(<ChatWindow onClose={jest.fn()} onNewMessage={jest.fn()} />);
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    expect(sendButton).toBeDisabled();
  });

  it('calls onClose when close button is clicked', () => {
    const mockOnClose = jest.fn();
    renderWithProviders(<ChatWindow onClose={mockOnClose} onNewMessage={jest.fn()} />);
    
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);
    
    expect(mockOnClose).toHaveBeenCalled();
  });
});
