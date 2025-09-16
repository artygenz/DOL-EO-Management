import React, { useState } from 'react';
import { 
  Fab, 
  Badge, 
  Tooltip,
  useTheme,
  useMediaQuery
} from '@mui/material';
import { 
  Chat as ChatIcon, 
  Close as CloseIcon 
} from '@mui/icons-material';
import ChatWindow from './ChatWindow';

const FloatingChatIcon = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [hasUnreadMessages, setHasUnreadMessages] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const handleToggle = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      setHasUnreadMessages(false);
    }
  };

  const handleNewMessage = () => {
    if (!isOpen) {
      setHasUnreadMessages(true);
    }
  };

  return (
    <>
      {/* Floating Chat Icon */}
      <Fab
        color="primary"
        aria-label="chat"
        onClick={handleToggle}
        sx={{
          position: 'fixed',
          bottom: isMobile ? 16 : 24,
          right: isMobile ? 16 : 24,
          zIndex: 1000,
          boxShadow: theme.shadows[8],
          '&:hover': {
            boxShadow: theme.shadows[12],
            transform: 'scale(1.05)',
          },
          transition: 'all 0.3s ease-in-out',
        }}
      >
        <Tooltip title={isOpen ? "Close Chat" : "Open Chat"}>
          <Badge 
            color="error" 
            variant="dot" 
            invisible={!hasUnreadMessages}
          >
            {isOpen ? <CloseIcon /> : <ChatIcon />}
          </Badge>
        </Tooltip>
      </Fab>

      {/* Chat Window */}
      {isOpen && (
        <ChatWindow
          onClose={() => setIsOpen(false)}
          onNewMessage={handleNewMessage}
        />
      )}
    </>
  );
};

export default FloatingChatIcon;
