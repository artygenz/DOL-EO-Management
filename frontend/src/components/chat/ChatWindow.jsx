import React, { useState, useEffect, useRef } from 'react';
import { flushSync } from 'react-dom';
import ReactMarkdown from 'react-markdown';
import {
  Paper,
  Box,
  Typography,
  TextField,
  IconButton,
  Avatar,
  Divider,
  Chip,
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
  Close as CloseIcon
} from '@mui/icons-material';
import { useAuth } from '../../hooks/useAuth';

const ChatWindow = ({ onClose, onNewMessage }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const messagesEndRef = useRef(null);
  const streamingMessageRef = useRef(null);
  const { user } = useAuth();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  // Send initial greeting when chat opens
  useEffect(() => {
    if (user && messages.length === 0) {
      const greeting = getRoleBasedGreeting(user);
      setMessages([{
        id: Date.now(),
        type: 'bot',
        content: greeting,
        timestamp: new Date()
      }]);
    }
  }, [user, messages.length]);

  const getRoleBasedGreeting = (user) => {
    const roleGreetings = {
      admin: `Hello ${user.name || 'Admin'}! I'm your AI assistant. I can help you manage the system, review tasks, and provide insights. How can I assist you today?`,
      reviewer: `Hi ${user.name || 'Reviewer'}! I'm here to help you review tasks, analyze data, and provide recommendations. What would you like to know?`,
      executor: `Hello ${user.name || 'Executor'}! I can help you with your tasks, provide updates, and answer questions about your work. How can I help you today?`
    };
    return roleGreetings[user.role] || `Hello ${user.name || 'User'}! I'm your AI assistant. How can I help you today?`;
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setIsStreaming(true);
    setStreamingMessage('');

    try {
      // Use streaming endpoint by default
      console.log('Sending message to chat stream:', {
        message: inputMessage.trim(),
        context: { role: user.role, user_id: user.id }
      });
      
      const response = await fetch('/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive'
        },
        body: JSON.stringify({
          message: inputMessage.trim(),
          context: {
            role: user.role,
            user_id: user.id
          }
        })
      });

      console.log('Response status:', response.status, response.statusText);
      console.log('Response headers:', Object.fromEntries(response.headers.entries()));
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Response error:', errorText);
        throw new Error(`Failed to send message: ${response.status} ${response.statusText}`);
      }

      if (!response.body) {
        console.error('No response body available for streaming');
        throw new Error('No response body available for streaming');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      const processStreamChunk = async (chunk, currentResponse, setStreamingCallback) => {
        const lines = chunk.split('\n');
        let updatedResponse = currentResponse;

        for (const line of lines) {
          // Handle SSE format: data: <json>
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6).trim();
              if (jsonStr === '') continue; // Skip empty data lines
              
              const data = JSON.parse(jsonStr);
              console.log('Parsed streaming data:', data);
              
              if (data.type === 'chunk') {
                updatedResponse += data.content;
                console.log('Updated fullResponse:', updatedResponse);
                // Force immediate UI update
                setStreamingCallback(updatedResponse);
                // Add a small delay to make streaming more visible
                await new Promise(resolve => setTimeout(resolve, 5));
              } else if (data.type === 'complete') {
                console.log('Stream complete, adding message:', updatedResponse);
                // Add the complete message to messages
                setMessages(prev => [...prev, {
                  id: Date.now() + 1,
                  type: 'bot',
                  content: updatedResponse,
                  timestamp: new Date()
                }]);
                setStreamingMessage('');
                setIsStreaming(false);
                return { done: true, response: updatedResponse };
              } else if (data.type === 'error') {
                throw new Error(data.message);
              } else if (data.type === 'metadata') {
                console.log('Received metadata:', data);
                // Continue processing, don't update response
              }
            } catch (e) {
              console.error('Error parsing streaming data:', e, 'Line:', line);
            }
          } else if (line.trim() === '') {
            // Empty line in SSE - this is normal, continue
            continue;
          } else if (line.startsWith('event: ')) {
            // SSE event type - log for debugging
            console.log('SSE event type:', line.slice(7));
          } else if (line.startsWith('id: ')) {
            // SSE event ID - log for debugging
            console.log('SSE event ID:', line.slice(4));
          } else {
            // Unknown line format - log for debugging
            console.log('Unknown SSE line format:', line);
          }
        }
        
        return { done: false, response: updatedResponse };
      };

      const processStream = async () => {
        try {
          let hasReceivedData = false;
          let lastDataTime = Date.now();
          const STREAM_TIMEOUT = 10000; // 10 seconds timeout
          
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            console.log('Received chunk:', chunk);
            hasReceivedData = true;
            lastDataTime = Date.now();
            
            const result = await processStreamChunk(chunk, fullResponse, (newText) => {
              flushSync(() => {
                setStreamingMessage(newText);
              });
              // Also directly update DOM for immediate visual feedback
              if (streamingMessageRef.current) {
                // Find the first text node and update it
                const textNode = streamingMessageRef.current.querySelector('p');
                if (textNode) {
                  textNode.textContent = newText;
                } else {
                  streamingMessageRef.current.textContent = newText;
                }
              }
            });
            fullResponse = result.response;
            
            if (result.done) {
              return;
            }
            
            // Check for timeout
            if (Date.now() - lastDataTime > STREAM_TIMEOUT) {
              console.log('Stream timeout, falling back to non-streaming');
              throw new Error('Stream timeout');
            }
          }
          
          // If we received data but no completion signal, treat as complete
          if (hasReceivedData && fullResponse) {
            console.log('Stream ended without completion signal, treating as complete');
            setMessages(prev => [...prev, {
              id: Date.now() + 1,
              type: 'bot',
              content: fullResponse,
              timestamp: new Date()
            }]);
            setStreamingMessage('');
            setIsStreaming(false);
          } else if (!hasReceivedData) {
            // If no data was received, the streaming might be buffered
            console.log('No streaming data received, response might be buffered');
            // Fall back to non-streaming endpoint
            throw new Error('No streaming data received');
          }
        } catch (streamError) {
          console.error('Streaming error:', streamError);
          throw streamError;
        }
      };

      await processStream();
    } catch (error) {
      console.error('Chat streaming error:', error);
      
      // Fallback to non-streaming endpoint
      try {
        console.log('Falling back to non-streaming endpoint');
        const fallbackResponse = await fetch('/chat/query', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({
            message: inputMessage.trim(),
            context: {
              role: user.role,
              user_id: user.id
            }
          })
        });

        if (fallbackResponse.ok) {
          const fallbackData = await fallbackResponse.json();
          const responseText = fallbackData.response || 'No response received';
          
          // Simulate streaming by displaying text character by character
          console.log('Simulating streaming for fallback response');
          setIsStreaming(true);
          setStreamingMessage('');
          
          let currentText = '';
          for (let i = 0; i < responseText.length; i++) {
            currentText += responseText[i];
            setStreamingMessage(currentText);
            await new Promise(resolve => setTimeout(resolve, 20)); // 20ms delay per character
          }
          
          // Add the complete message
          setMessages(prev => [...prev, {
            id: Date.now() + 1,
            type: 'bot',
            content: responseText,
            timestamp: new Date()
          }]);
          setStreamingMessage('');
          setIsStreaming(false);
        } else {
          throw new Error('Fallback also failed');
        }
      } catch (fallbackError) {
        console.error('Fallback error:', fallbackError);
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          type: 'bot',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date()
        }]);
      }
      
      setStreamingMessage('');
      setIsStreaming(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  };

  // Test function to simulate streaming (for debugging)
  const testStreaming = () => {
    const testMessage = "This is a test streaming message that should appear word by word.";
    const words = testMessage.split(' ');
    let currentText = '';
    
    setIsStreaming(true);
    setStreamingMessage('');
    
    const interval = setInterval(() => {
      if (words.length === 0) {
        clearInterval(interval);
        setMessages(prev => [...prev, {
          id: Date.now(),
          type: 'bot',
          content: currentText,
          timestamp: new Date()
        }]);
        setStreamingMessage('');
        setIsStreaming(false);
        return;
      }
      
      const word = words.shift();
      currentText += (currentText ? ' ' : '') + word;
      setStreamingMessage(currentText);
    }, 200);
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <Slide direction="up" in={true} timeout={300}>
      <Paper
        elevation={8}
        sx={{
          position: 'fixed',
          bottom: isMobile ? 80 : 100,
          right: isMobile ? 16 : 24,
          width: isMobile ? 'calc(100vw - 32px)' : 400,
          height: 500,
          zIndex: 999,
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 2,
          overflow: 'hidden',
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        {/* Header */}
        <Box
          sx={{
            p: 2,
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.light' }}>
              <BotIcon />
            </Avatar>
            <Box>
              <Typography variant="subtitle1" fontWeight="bold">
                AI Assistant
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.8 }}>
                {user?.role && (
                  <Chip 
                    label={user.role.charAt(0).toUpperCase() + user.role.slice(1)} 
                    size="small" 
                    sx={{ 
                      height: 16, 
                      fontSize: '0.7rem',
                      bgcolor: 'rgba(255,255,255,0.2)',
                      color: 'inherit'
                    }} 
                  />
                )}
              </Typography>
            </Box>
          </Box>
          <IconButton 
            onClick={testStreaming} 
            size="small"
            sx={{ color: 'inherit', mr: 1 }}
            title="Test Streaming"
          >
            <Typography variant="caption" sx={{ fontSize: '0.7rem' }}>TEST</Typography>
          </IconButton>
          <IconButton 
            onClick={onClose} 
            size="small"
            sx={{ color: 'inherit' }}
          >
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Messages */}
        <Box
          sx={{
            flex: 1,
            overflow: 'auto',
            p: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: 1,
          }}
        >
          {messages.map((message) => (
            <Fade key={message.id} in={true} timeout={300}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start',
                  gap: 1,
                }}
              >
                {message.type === 'bot' && (
                  <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.light' }}>
                    <BotIcon />
                  </Avatar>
                )}
                <Box
                  sx={{
                    maxWidth: '70%',
                    bgcolor: message.type === 'user' ? 'primary.main' : 'grey.100',
                    color: message.type === 'user' ? 'primary.contrastText' : 'text.primary',
                    p: 1.5,
                    borderRadius: 2,
                    position: 'relative',
                  }}
                >
                  {message.type === 'bot' ? (
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => (
                          <Typography variant="body2" sx={{ wordBreak: 'break-word', mb: 1 }}>
                            {children}
                          </Typography>
                        ),
                        strong: ({ children }) => (
                          <Typography component="span" sx={{ fontWeight: 'bold' }}>
                            {children}
                          </Typography>
                        ),
                        em: ({ children }) => (
                          <Typography component="span" sx={{ fontStyle: 'italic' }}>
                            {children}
                          </Typography>
                        ),
                        ul: ({ children }) => (
                          <Box component="ul" sx={{ pl: 2, mb: 1 }}>
                            {children}
                          </Box>
                        ),
                        ol: ({ children }) => (
                          <Box component="ol" sx={{ pl: 2, mb: 1 }}>
                            {children}
                          </Box>
                        ),
                        li: ({ children }) => (
                          <Typography component="li" variant="body2" sx={{ mb: 0.5 }}>
                            {children}
                          </Typography>
                        ),
                        code: ({ children }) => (
                          <Typography
                            component="code"
                            sx={{
                              backgroundColor: 'grey.100',
                              px: 0.5,
                              py: 0.25,
                              borderRadius: 0.5,
                              fontFamily: 'monospace',
                              fontSize: '0.875em'
                            }}
                          >
                            {children}
                          </Typography>
                        ),
                        pre: ({ children }) => (
                          <Box
                            component="pre"
                            sx={{
                              backgroundColor: 'grey.100',
                              p: 1,
                              borderRadius: 1,
                              overflow: 'auto',
                              mb: 1
                            }}
                          >
                            {children}
                          </Box>
                        )
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  ) : (
                    <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
                      {message.content}
                    </Typography>
                  )}
                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      mt: 0.5,
                      opacity: 0.7,
                      fontSize: '0.7rem',
                    }}
                  >
                    {formatTime(message.timestamp)}
                  </Typography>
                </Box>
                {message.type === 'user' && (
                  <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main' }}>
                    <PersonIcon />
                  </Avatar>
                )}
              </Box>
            </Fade>
          ))}

          {/* Streaming message */}
          {isStreaming && (
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'flex-start',
                gap: 1,
              }}
            >
              <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.light' }}>
                <BotIcon />
              </Avatar>
              <Box
                sx={{
                  maxWidth: '70%',
                  bgcolor: 'grey.100',
                  color: 'text.primary',
                  p: 1.5,
                  borderRadius: 2,
                  position: 'relative',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                  <Box sx={{ flex: 1 }} ref={streamingMessageRef}>
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => (
                          <Typography variant="body2" sx={{ wordBreak: 'break-word', mb: 1 }}>
                            {children}
                          </Typography>
                        ),
                        strong: ({ children }) => (
                          <Typography component="span" sx={{ fontWeight: 'bold' }}>
                            {children}
                          </Typography>
                        ),
                        em: ({ children }) => (
                          <Typography component="span" sx={{ fontStyle: 'italic' }}>
                            {children}
                          </Typography>
                        ),
                        ul: ({ children }) => (
                          <Box component="ul" sx={{ pl: 2, mb: 1 }}>
                            {children}
                          </Box>
                        ),
                        ol: ({ children }) => (
                          <Box component="ol" sx={{ pl: 2, mb: 1 }}>
                            {children}
                          </Box>
                        ),
                        li: ({ children }) => (
                          <Typography component="li" variant="body2" sx={{ mb: 0.5 }}>
                            {children}
                          </Typography>
                        ),
                        code: ({ children }) => (
                          <Typography
                            component="code"
                            sx={{
                              backgroundColor: 'grey.100',
                              px: 0.5,
                              py: 0.25,
                              borderRadius: 0.5,
                              fontFamily: 'monospace',
                              fontSize: '0.875em'
                            }}
                          >
                            {children}
                          </Typography>
                        )
                      }}
                    >
                      {streamingMessage || 'Thinking...'}
                    </ReactMarkdown>
                  </Box>
                  <CircularProgress size={12} sx={{ mt: 0.5 }} />
                </Box>
              </Box>
            </Box>
          )}

          <div ref={messagesEndRef} />
        </Box>

        <Divider />

        {/* Input */}
        <Box sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
            <TextField
              fullWidth
              multiline
              maxRows={3}
              placeholder="Type your message..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
              variant="outlined"
              size="small"
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                },
              }}
            />
            <IconButton
              onClick={handleSendMessage}
              disabled={!inputMessage.trim() || isLoading}
              color="primary"
              sx={{
                bgcolor: 'primary.main',
                color: 'primary.contrastText',
                '&:hover': {
                  bgcolor: 'primary.dark',
                },
                '&:disabled': {
                  bgcolor: 'grey.300',
                  color: 'grey.500',
                },
              }}
            >
              {isLoading ? (
                <CircularProgress size={20} color="inherit" />
              ) : (
                <SendIcon />
              )}
            </IconButton>
          </Box>
        </Box>
      </Paper>
    </Slide>
  );
};

export default ChatWindow;
