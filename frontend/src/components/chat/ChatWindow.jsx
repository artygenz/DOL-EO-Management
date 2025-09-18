import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Paper,
  Box,
  Typography,
  TextField,
  IconButton,
  Avatar,
  Divider,
  CircularProgress,
  useTheme,
  useMediaQuery,
  Fade,
  Slide
} from '@mui/material';
import {
  Send as SendIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
  Close as CloseIcon,
  BugReport as BugReportIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { useAuth } from '../../hooks/useAuth';
import api from '../../services/api';

const ChatWindow = ({ onClose, onNewMessage }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [debugInfo, setDebugInfo] = useState({
    parsedData: [],
    errors: [],
    connectionStatus: 'disconnected'
  });
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const messagesEndRef = useRef(null);
  const { user } = useAuth();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  // Show greeting message on mount
  useEffect(() => {
    if (messages.length === 0 && user) {
      const greetingMessage = {
        id: Date.now(),
        type: 'bot',
        content: `Hello! I'm your AI assistant. I can help you with tasks, executive orders, and other work-related queries. How can I assist you today?`,
        timestamp: new Date()
      };
      
      setTimeout(() => {
        setMessages([greetingMessage]);
      }, 300);
    }
  }, [user, messages.length]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    };

    console.log('👤 Adding user message:', userMessage);
    setMessages(prev => {
      const newMessages = [...prev, userMessage];
      console.log('📝 Updated messages array after user message:', newMessages);
      return newMessages;
    });
    setInputMessage('');
    setIsLoading(true);
    setDebugInfo({
      parsedData: [],
      errors: [],
      connectionStatus: 'connecting'
    });

    try {
      console.log('🚀 Sending message to query endpoint...');
      
      const response = await api.post('/chat/query', {
        message: inputMessage.trim(),
        context: {
          role: user.role,
          user_id: user.id
        }
      }, {
        timeout: 30000, // 30 seconds timeout for chat requests
        headers: {
          'Cache-Control': 'no-cache'
        }
      });

      console.log('📊 Response status:', response.status);
      const data = response.data;
      console.log('🎯 Response data:', data);

      // Update debug info
      setDebugInfo(prev => ({
        ...prev,
        parsedData: [{
          timestamp: new Date().toLocaleTimeString(),
          type: 'response',
          content: `Tool: ${data.tool || 'none'}, Response length: ${data.response?.length || 0}`
        }],
        connectionStatus: 'completed'
      }));

      // Add bot response
      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: data.response || 'No response received',
        timestamp: new Date(),
        tool: data.tool,
        args: data.args,
        data: data.data,
        processing: data.processing
      };
      
      console.log('🤖 Adding bot message:', botMessage);
      setMessages(prev => {
        const newMessages = [...prev, botMessage];
        console.log('📝 Updated messages array:', newMessages);
        return newMessages;
      });
      
      // Call onNewMessage callback if provided
      if (onNewMessage) {
        onNewMessage(botMessage);
      }
      
    } catch (error) {
      console.error('❌ Chat error:', error);
      
      // Determine user-friendly error message
      let errorMessage = 'Sorry, something went wrong. Please try again.';
      
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        errorMessage = '⏱️ Request timed out. The server is taking too long to respond. Please try again with a simpler question or check your connection.';
      } else if (error.response?.status === 500) {
        errorMessage = '🔧 Server error occurred. Our team has been notified. Please try again in a few moments.';
      } else if (error.response?.status === 401) {
        errorMessage = '🔐 Authentication expired. Please refresh the page and log in again.';
      } else if (error.response?.status === 403) {
        errorMessage = '🚫 You don\'t have permission to perform this action.';
      } else if (error.response?.status >= 400 && error.response?.status < 500) {
        errorMessage = '📝 There was an issue with your request. Please check your input and try again.';
      } else if (!navigator.onLine) {
        errorMessage = '🌐 You appear to be offline. Please check your internet connection and try again.';
      } else if (error.userMessage) {
        errorMessage = error.userMessage;
      }
      
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        type: 'bot',
        content: errorMessage,
        timestamp: new Date(),
        isError: true
      }]);
      setDebugInfo(prev => ({
        ...prev,
        errors: [...prev.errors, { 
          timestamp: new Date().toLocaleTimeString(), 
          error: error.message,
          userMessage: errorMessage
        }],
        connectionStatus: 'error'
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleRetryMessage = (messageId) => {
    // Find the message before the error message
    const messageIndex = messages.findIndex(msg => msg.id === messageId);
    if (messageIndex > 0) {
      const previousMessage = messages[messageIndex - 1];
      if (previousMessage.type === 'user') {
        // Remove the error message and retry with the previous user message
        setMessages(prev => prev.filter(msg => msg.id !== messageId));
        setInputMessage(previousMessage.content);
        setTimeout(() => handleSendMessage(), 100);
      }
    }
  };

  // 🧪 TEST FUNCTION for query endpoint
  const testQuery = () => {
    setInputMessage('Show me my tasks');
    setTimeout(() => handleSendMessage(), 100);
  };

  return (
    <Slide direction="up" in={true} mountOnEnter unmountOnExit>
      <Paper
        elevation={8}
        sx={{
          position: 'fixed',
          bottom: isMobile ? 0 : 20,
          right: isMobile ? 0 : 20,
          width: isMobile ? '100vw' : 400,
          height: isMobile ? '100vh' : 600,
          display: 'flex',
          flexDirection: 'column',
          zIndex: 1300,
          borderRadius: isMobile ? 0 : 2
        }}
      >
        {/* Header */}
        <Box sx={{ 
          p: 2, 
          borderBottom: 1, 
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          bgcolor: 'primary.main',
          color: 'primary.contrastText'
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <BotIcon color="primary" />
            <Typography variant="h6">AI Assistant {user?.role && `(${user.role})`}</Typography>
          </Box>
          <Box>
            <IconButton 
              onClick={testQuery}
              size="small"
              sx={{ color: 'inherit', mr: 1 }}
              title="Test Query"
            >
              <Typography variant="caption" sx={{ fontSize: '0.7rem' }}>TEST</Typography>
            </IconButton>
            <IconButton 
              onClick={() => setShowDebugPanel(!showDebugPanel)} 
              size="small"
              sx={{ color: 'inherit', mr: 1 }}
              title="Toggle Debug Panel"
            >
              <BugReportIcon fontSize="small" />
            </IconButton>
            <IconButton 
              onClick={onClose} 
              size="small"
              sx={{ color: 'inherit' }}
              title="Close Chat"
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        </Box>

        {/* Messages */}
        <Box sx={{ 
          flex: 1, 
          overflow: 'auto', 
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 1
        }}>
          {console.log('🎨 Rendering messages:', messages.length, 'messages')}
          {messages.map((message) => {
            console.log('🎨 Rendering message:', message.id, message.type, message.content?.substring(0, 50));
            return (
            <Fade key={message.id} in={true} timeout={300}>
              <Box sx={{ 
                display: 'flex', 
                justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start',
                mb: 2,
                gap: 1
              }}>
                {message.type === 'bot' && (
                  <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
                    <BotIcon />
                  </Avatar>
                )}
                <Box sx={{ 
                  maxWidth: '80%', 
                  p: 2, 
                  borderRadius: 2,
                  bgcolor: message.type === 'user' 
                    ? 'primary.main' 
                    : message.isError 
                      ? 'error.light' 
                      : 'grey.100',
                  color: message.type === 'user' 
                    ? 'primary.contrastText' 
                    : message.isError 
                      ? 'error.contrastText' 
                      : 'text.primary',
                  border: message.isError ? '1px solid' : 'none',
                  borderColor: message.isError ? 'error.main' : 'transparent'
                }}>
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                  {message.tool && !message.isError && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                      Tool: {message.tool}
                    </Typography>
                  )}
                  {message.isError && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                      <IconButton 
                        size="small" 
                        onClick={() => handleRetryMessage(message.id)}
                        sx={{ 
                          color: 'inherit',
                          '&:hover': { bgcolor: 'rgba(255,255,255,0.1)' }
                        }}
                        title="Retry this request"
                      >
                        <RefreshIcon fontSize="small" />
                      </IconButton>
                      <Typography variant="caption" sx={{ opacity: 0.8 }}>
                        Click to retry
                      </Typography>
                    </Box>
                  )}
                </Box>
                {message.type === 'user' && (
                  <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main' }}>
                    <PersonIcon />
                  </Avatar>
                )}
              </Box>
            </Fade>
            );
          })}

          {/* Loading indicator */}
          {isLoading && (
            <Box sx={{ 
              display: 'flex', 
              justifyContent: 'flex-start',
              mb: 2,
              gap: 1
            }}>
              <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
                <BotIcon />
              </Avatar>
              <Box sx={{ 
                maxWidth: '80%', 
                p: 2, 
                borderRadius: 2,
                bgcolor: 'grey.100',
                display: 'flex',
                alignItems: 'center',
                gap: 1
              }}>
                <CircularProgress size={16} />
                <Typography variant="body2" color="text.secondary">
                  Thinking...
                </Typography>
              </Box>
            </Box>
          )}

          <div ref={messagesEndRef} />
        </Box>

        <Divider />

        {/* Input */}
        <Box sx={{ p: 2 }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            disabled={isLoading}
            InputProps={{
              endAdornment: (
                <IconButton 
                  onClick={handleSendMessage} 
                  disabled={!inputMessage.trim() || isLoading}
                  color="primary"
                >
                  <SendIcon />
                </IconButton>
              )
            }}
          />
        </Box>

        {/* Debug Panel */}
        {showDebugPanel && (
          <Box sx={{ 
            p: 2, 
            bgcolor: '#f5f5f5', 
            maxHeight: '200px', 
            overflow: 'auto' 
          }}>
            <Typography variant="h6" gutterBottom>🐛 Query Debug</Typography>
            
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2">Status: {debugInfo.connectionStatus}</Typography>
            </Box>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle2">Response Data ({debugInfo.parsedData.length})</Typography>
                {debugInfo.parsedData.map((data, i) => (
                  <Box key={i} sx={{ fontSize: '0.8rem', mb: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">
                      {data.timestamp} - {data.type}
                    </Typography>
                    <Typography variant="caption" sx={{ display: 'block', fontFamily: 'monospace' }}>
                      {data.content}
                    </Typography>
                  </Box>
                ))}
              </Box>

              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle2">Errors ({debugInfo.errors.length})</Typography>
                {debugInfo.errors.map((error, i) => (
                  <Box key={i} sx={{ fontSize: '0.8rem', mb: 0.5 }}>
                    <Typography variant="caption" color="error">
                      {error.timestamp} - {error.error}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          </Box>
        )}
      </Paper>
    </Slide>
  );
};

export default ChatWindow;
