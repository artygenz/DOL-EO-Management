import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import FloatingChatIcon from '../FloatingChatIcon';
import authSlice from '../../../store/slices/authSlice';

// Mock the ChatWindow component
jest.mock('../ChatWindow', () => {
  return function MockChatWindow({ onClose }) {
    return (
      <div data-testid="chat-window">
        <button onClick={onClose}>Close Chat</button>
      </div>
    );
  };
});

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

describe('FloatingChatIcon', () => {
  it('renders the chat icon', () => {
    renderWithProviders(<FloatingChatIcon />);
    
    const chatButton = screen.getByRole('button', { name: /chat/i });
    expect(chatButton).toBeInTheDocument();
  });

  it('shows chat icon when closed', () => {
    renderWithProviders(<FloatingChatIcon />);
    
    const chatButton = screen.getByRole('button', { name: /chat/i });
    expect(chatButton).toBeInTheDocument();
  });

  it('opens chat window when clicked', () => {
    renderWithProviders(<FloatingChatIcon />);
    
    const chatButton = screen.getByRole('button', { name: /chat/i });
    fireEvent.click(chatButton);
    
    expect(screen.getByTestId('chat-window')).toBeInTheDocument();
  });

  it('shows close icon when chat is open', () => {
    renderWithProviders(<FloatingChatIcon />);
    
    const chatButton = screen.getByRole('button', { name: /chat/i });
    fireEvent.click(chatButton);
    
    // The button should now show close icon
    expect(chatButton).toBeInTheDocument();
  });

  it('closes chat window when close button is clicked', () => {
    renderWithProviders(<FloatingChatIcon />);
    
    const chatButton = screen.getByRole('button', { name: /chat/i });
    fireEvent.click(chatButton);
    
    expect(screen.getByTestId('chat-window')).toBeInTheDocument();
    
    const closeButton = screen.getByText('Close Chat');
    fireEvent.click(closeButton);
    
    expect(screen.queryByTestId('chat-window')).not.toBeInTheDocument();
  });
});
