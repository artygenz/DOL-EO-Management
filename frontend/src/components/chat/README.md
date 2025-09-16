# Chat Components

This directory contains the floating chat functionality for the DOL EO Management System.

## Components

### FloatingChatIcon
- A floating action button (FAB) positioned in the bottom-right corner
- Shows a chat icon that toggles to a close icon when the chat is open
- Includes a badge indicator for unread messages
- Responsive design that adapts to mobile and desktop screens

### ChatWindow
- A slide-up chat interface that appears when the floating icon is clicked
- Features:
  - Role-based greeting messages
  - Real-time streaming responses from the AI assistant
  - Message history with timestamps
  - User and bot message differentiation
  - Responsive design for mobile and desktop
  - Auto-scroll to latest messages
  - Loading states and error handling

## Features

### Authentication Integration
- Only shows for authenticated users
- Uses user role and name for personalized greetings
- Sends user context (role, user_id) with each message

### Streaming Support
- Uses the `/chat/stream` endpoint by default
- Real-time message streaming with visual indicators
- Handles streaming errors gracefully

### Role-Based Greetings
- **Admin**: "Hello [Name]! I'm your AI assistant. I can help you manage the system, review tasks, and provide insights. How can I assist you today?"
- **Reviewer**: "Hi [Name]! I'm here to help you review tasks, analyze data, and provide recommendations. What would you like to know?"
- **Executor**: "Hello [Name]! I can help you with your tasks, provide updates, and answer questions about your work. How can I help you today?"

### Responsive Design
- Mobile-optimized with appropriate sizing
- Desktop version with fixed dimensions (400px width, 500px height)
- Smooth animations and transitions

## Usage

The chat components are automatically included in the `AppShell` component and will appear on all authenticated pages. No additional setup is required.

## API Integration

The chat components integrate with the backend chat API:
- **Streaming Endpoint**: `/chat/stream` (used by default)
- **Non-streaming Endpoint**: `/chat/query` (fallback)
- **Authentication**: Uses Bearer token from localStorage
- **Context**: Sends user role and ID with each request

## Styling

The components use Material-UI theming and are fully integrated with the application's theme system, supporting both light and dark modes.
