# FrontShiftAI Frontend

React-based user interface for the FrontShiftAI multi-tenant RAG system, providing intuitive access to company handbooks, PTO management, and HR support ticketing across multiple organizations.

## Quick Start

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Access application: http://localhost:5173

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React Components
│   │   ├── ChatArea.jsx             # Message display area
│   │   ├── MessageInput.jsx         # Chat input interface
│   │   ├── Sidebar.jsx              # Navigation sidebar
│   │   ├── UserChatPage.jsx         # Main chat container with tabs
│   │   ├── PTORequestsTab.jsx       # PTO requests view
│   │   ├── HRTicketsTab.jsx         # HR tickets view with admin notes
│   │   ├── Login.jsx                # Authentication interface
│   │   ├── ConnectionStatus.jsx     # Backend connection indicator
│   │   ├── CompanyAdminDashboard.jsx  # Company admin interface
│   │   └── SuperAdminDashboard.jsx    # Super admin interface
│   │
│   ├── services/            # API Integration
│   │   └── api.js          # API client and endpoints
│   │
│   ├── App.jsx             # Root application component
│   ├── main.jsx            # Application entry point
│   └── index.css           # Global styles and Tailwind
│
├── public/                 # Static assets
├── .env                    # Environment configuration
├── package.json           # Dependencies and scripts
├── tailwind.config.js     # Tailwind CSS configuration
├── postcss.config.js      # PostCSS configuration
├── vite.config.js         # Vite build configuration
└── index.html             # HTML entry point
```

## Architecture

### User Flow

The application supports three distinct user roles with role-based routing:

**Regular Users:**
- Tab-based interface for seamless navigation
- Chat tab for unified agent interactions (RAG, PTO, HR)
- PTO Requests tab for viewing time-off history and balances
- HR Tickets tab for viewing support requests and admin notes

**Company Admins:**
- PTO request management (approve/deny)
- Employee PTO balance administration
- HR ticket queue management
- Meeting scheduling and note communication

**Super Admins:**
- Multi-company user management
- System-wide administration
- Company configuration

### Component Hierarchy

```
App.jsx
├── Login.jsx (unauthenticated)
├── SuperAdminDashboard.jsx (super_admin role)
├── CompanyAdminDashboard.jsx (company_admin role)
└── Regular User Interface (user role)
    ├── Sidebar.jsx
    │   ├── Logo
    │   ├── User Info
    │   ├── Search Bar
    │   └── Recent Chats
    │
    └── UserChatPage.jsx
        ├── Tab Navigation (Chat | PTO Requests | HR Tickets)
        ├── Chat Tab
        │   ├── ChatArea.jsx (message display)
        │   └── MessageInput.jsx (input interface)
        │
        ├── PTORequestsTab.jsx
        │   ├── Balance Overview
        │   └── Request History
        │
        └── HRTicketsTab.jsx
            ├── Ticket List
            └── Ticket Details (with admin notes)
```

## Key Features

### Unified Chat Interface

The chat interface provides seamless interaction with multiple AI agents through a single conversation flow.

**Implementation:**
```javascript
// App.jsx - Message Handler
const handleSendMessage = async (message) => {
  // Send to unified router endpoint
  const response = await axios.post(
    `${API_BASE_URL}/api/chat/message`,
    { message },
    { headers: { Authorization: `Bearer ${token}` }}
  );
  
  // Response includes agent_used field
  const assistantMessage = {
    role: 'assistant',
    content: response.data.response,
    agentType: response.data.agent_used,
    // Agent-specific metadata preserved
    ...metadata
  };
};
```

**Agent Routing:**
- User queries automatically routed to appropriate agent (RAG, PTO, HR Ticket)
- Seamless context switching between agent types
- Unified response format across all agents

**Example Conversation:**
```
User: "What is the remote work policy?"
System: [RAG Agent] According to the handbook...

User: "I need 3 days off next week"
System: [PTO Agent] PTO request created...

User: "Schedule a meeting with HR about benefits"
System: [HR Ticket Agent] Support ticket created...
```

### Tab-Based Navigation

**Chat Tab:**
- Primary interface for all requests
- Natural language processing for all agent types
- Real-time message streaming
- Source attribution for RAG responses
- Message persistence across sessions

**PTO Requests Tab:**
- Visual balance dashboard showing:
  - Available days
  - Used days
  - Pending days
  - Total allocation
- Request history with status indicators
- Detailed request information (dates, reason, admin notes)
- Color-coded status badges (pending, approved, denied)

**HR Tickets Tab:**
- Comprehensive ticket listing
- Expandable ticket details
- Admin notes visibility for transparent communication
- Status tracking (pending, in_progress, scheduled, resolved, closed)
- Meeting information display
- Category icons for quick identification

### HR Ticket Notes System

Admin notes are prominently displayed to users for transparent communication.

**Display Features:**
```javascript
// HRTicketsTab.jsx - Notes Section
{ticket.notes && ticket.notes.length > 0 && (
  <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
    <p className="text-xs text-blue-400 mb-3 font-medium">Admin Notes:</p>
    <div className="space-y-3">
      {ticket.notes.map((note, idx) => (
        <div key={idx} className="bg-white/5 rounded-lg p-3">
          <div className="flex items-start justify-between mb-2">
            <span className="text-xs text-white/50">
              {note.admin_email || 'Admin'}
            </span>
            <span className="text-xs text-white/40">
              {new Date(note.created_at).toLocaleDateString()}
            </span>
          </div>
          <p className="text-sm text-white/90">{note.note}</p>
        </div>
      ))}
    </div>
  </div>
)}
```

**Note Characteristics:**
- Chronological display with timestamps
- Admin attribution
- Highlighted presentation for visibility
- Real-time updates when fetching ticket details

### Clean Sidebar Design

**Features:**
- Company logo and branding
- User information display (email, company)
- Chat history with search functionality
- New chat creation
- Session management (logout)

**Removed Elements:**
- No auto-populated PTO balance section
- No recent PTO requests preview
- No HR tickets preview
- All status information moved to dedicated tabs

**Rationale:**
- Cleaner, less cluttered interface
- Clear separation between navigation and status views
- Dedicated tabs provide comprehensive information
- Reduced cognitive load

### Authentication & Authorization

**JWT-Based Authentication:**
```javascript
// services/api.js
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Automatic token injection
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Automatic logout on 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      logout();
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);
```

**Session Management:**
- Token stored in localStorage
- Automatic token validation on mount
- Persistent sessions across page refreshes
- Automatic logout on token expiration

**Role-Based Routing:**
```javascript
// App.jsx - Role-Based Display
if (userInfo?.role === 'super_admin') {
  return <SuperAdminDashboard />;
}

if (userInfo?.role === 'company_admin') {
  return <CompanyAdminDashboard />;
}

// Regular user interface
return <UserChatInterface />;
```

### Chat History Management

**Features:**
- Automatic conversation saving
- Time-based grouping (Today, Yesterday, This Week, etc.)
- Chat search functionality
- Individual chat deletion
- Chat restoration on selection

**Implementation:**
```javascript
// App.jsx - Chat History State
const [chatHistory, setChatHistory] = useState(() => {
  const saved = localStorage.getItem('chatHistory');
  return saved ? JSON.parse(saved) : [];
});

// Save to localStorage on change
useEffect(() => {
  localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}, [chatHistory]);

// Group by time
const groupedChats = chatHistory.reduce((groups, chat) => {
  const timeLabel = getTimeLabel(chat.timestamp);
  if (!groups[timeLabel]) {
    groups[timeLabel] = [];
  }
  groups[timeLabel].push(chat);
  return groups;
}, {});
```

### Responsive Design

**Tailwind CSS Implementation:**
- Mobile-first approach
- Adaptive layouts for different screen sizes
- Touch-friendly interface elements
- Responsive sidebar with resizing capability

**Glassmorphism Design:**
```css
/* index.css - Glass Effect */
.glass-card {
  @apply backdrop-blur-xl bg-white/10 border border-white/10 rounded-2xl;
}

.sidebar-glass {
  background: rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
}
```

**Visual Effects:**
- Floating orb animations
- Smooth transitions
- Hover states
- Loading animations

### Error Handling

**Connection Status Indicator:**
```javascript
// ConnectionStatus.jsx
const [isConnected, setIsConnected] = useState(true);

useEffect(() => {
  const checkConnection = async () => {
    try {
      await axios.get(`${API_BASE_URL}/docs`);
      setIsConnected(true);
    } catch (error) {
      setIsConnected(false);
    }
  };
  
  const interval = setInterval(checkConnection, 30000);
  return () => clearInterval(interval);
}, []);
```

**Error Messages:**
- Network connectivity issues
- Authentication failures
- API errors with context
- User-friendly error descriptions

## API Integration

### Service Layer

All API interactions are centralized in `src/services/api.js`:

**Authentication:**
```javascript
export const login = async (email, password) => {
  const response = await axios.post(`${API_BASE_URL}/api/auth/login`, {
    email,
    password,
  });
  
  localStorage.setItem('access_token', response.data.access_token);
  localStorage.setItem('user_email', response.data.email);
  localStorage.setItem('user_company', response.data.company);
  
  return response.data;
};

export const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_email');
  localStorage.removeItem('user_company');
};

export const getUserInfo = async () => {
  const response = await apiClient.get('/api/auth/me');
  return response.data;
};
```

**Unified Chat:**
```javascript
export const sendChatMessage = async (message) => {
  const response = await apiClient.post('/api/chat/message', { message });
  return response.data;
};
```

**PTO Management:**
```javascript
export const getPTOBalance = async () => {
  const response = await apiClient.get('/api/pto/balance');
  return response.data;
};

export const getPTORequests = async () => {
  const response = await apiClient.get('/api/pto/requests');
  return response.data;
};
```

**HR Tickets:**
```javascript
export const getMyHRTickets = async () => {
  const response = await apiClient.get('/api/hr-tickets/my-tickets');
  return response.data;
};

export const getHRTicketDetails = async (ticketId) => {
  const response = await apiClient.get(`/api/hr-tickets/${ticketId}`);
  return response.data;
};
```

## Styling

### Tailwind CSS Configuration

```javascript
// tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Custom color palette
      },
      animation: {
        'float-orb': 'float 6s ease-in-out infinite',
        'pulse-glow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
```

### Design System

**Color Palette:**
- Primary: Dark background with gradient overlays
- Accent: White with varying opacity levels
- Status Colors:
  - Pending: Yellow (`text-yellow-400`)
  - Approved/Resolved: Green (`text-green-400`)
  - Denied/Closed: Red (`text-red-400`)
  - In Progress: Blue (`text-blue-400`)
  - Scheduled: Purple (`text-purple-400`)

**Typography:**
- Font Family: System font stack
- Headings: Bold, high contrast
- Body Text: White with 90% opacity
- Secondary Text: White with 50-60% opacity

**Spacing:**
- Consistent padding and margins using Tailwind's spacing scale
- Card padding: `px-6 py-4`
- Section spacing: `space-y-6`

## Development

### Environment Configuration

```bash
# .env
VITE_API_URL=http://localhost:8000
```

### Development Server

```bash
# Start with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Code Organization

**Component Structure:**
```javascript
// Standard component template
import React, { useState, useEffect } from 'react';
import { apiFunction } from '../services/api';

const ComponentName = ({ prop1, prop2 }) => {
  const [state, setState] = useState(initialValue);

  useEffect(() => {
    // Side effects
  }, [dependencies]);

  const handleEvent = () => {
    // Event handler logic
  };

  return (
    <div className="tailwind-classes">
      {/* JSX content */}
    </div>
  );
};

export default ComponentName;
```

**State Management:**
- React hooks for local state
- Props for parent-child communication
- localStorage for persistence
- No external state management library (Redux, etc.)

### Best Practices

**Component Guidelines:**
- Single responsibility principle
- Reusable, composable components
- Props validation through PropTypes or TypeScript
- Clear naming conventions

**Performance:**
- Memoization for expensive calculations
- Lazy loading for large components
- Debouncing for search inputs
- Efficient re-rendering strategies

**Accessibility:**
- Semantic HTML elements
- ARIA labels where necessary
- Keyboard navigation support
- Screen reader compatibility

## Testing

### Manual Testing Checklist

**Authentication:**
- [ ] Login with valid credentials
- [ ] Login with invalid credentials
- [ ] Session persistence across page refresh
- [ ] Automatic logout on token expiration
- [ ] Role-based routing (user, company_admin, super_admin)

**Chat Interface:**
- [ ] Send RAG query (handbook question)
- [ ] Send PTO request
- [ ] Send HR ticket request
- [ ] View agent type in responses
- [ ] Message persistence in chat history
- [ ] New chat creation
- [ ] Chat deletion
- [ ] Search functionality

**PTO Requests Tab:**
- [ ] View balance information
- [ ] View request history
- [ ] Expand request details
- [ ] Status badge display
- [ ] Admin notes display

**HR Tickets Tab:**
- [ ] View ticket list
- [ ] Expand ticket details
- [ ] View admin notes
- [ ] View meeting information
- [ ] Status indicators
- [ ] Refresh functionality

**Sidebar:**
- [ ] Clean design without auto-populated sections
- [ ] User information display
- [ ] Chat history display
- [ ] Search functionality
- [ ] Logout functionality

### Testing Tools

```bash
# Install testing dependencies
npm install --save-dev @testing-library/react @testing-library/jest-dom vitest

# Run tests (when implemented)
npm run test
```

## Deployment

### Build Process

```bash
# Production build
npm run build

# Output: dist/ directory
# - Optimized JavaScript bundles
# - Minified CSS
# - Static assets
```

### Environment Variables

**Production Configuration:**
```bash
# .env.production
VITE_API_URL=https://api.yourcompany.com
```

**Docker Build Arguments:**
The `VITE_API_URL` must be passed as a build argument during the Docker build process to be baked into the static files.

```bash
docker build --build-arg VITE_API_URL=https://api.yourcompany.com -t frontend .
```

### Hosting Options

**Static Hosting:**
- Vercel
- Netlify
- AWS S3 + CloudFront
- GitHub Pages

**Build Output:**
```
dist/
├── index.html
├── assets/
│   ├── index-[hash].js
│   ├── index-[hash].css
│   └── [other-assets]
└── favicon.ico
```

### Nginx Configuration Example

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    root /var/www/frontshiftai/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### Common Issues

**Backend Connection Failed:**
```bash
# Verify backend is running
curl http://localhost:8000/docs

# Check VITE_API_URL in .env
cat .env

# Ensure CORS is configured on backend
```

**Build Errors:**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
```

**Authentication Issues:**
```bash
# Clear localStorage
localStorage.clear()

# Check token in browser DevTools
localStorage.getItem('access_token')

# Verify token with backend
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/auth/me
```

**UI Not Updating:**
```bash
# Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
# Clear browser cache
# Check React DevTools for state changes
```

## Browser Support

**Supported Browsers:**
- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)

**Required Features:**
- ES6+ JavaScript support
- CSS Grid and Flexbox
- localStorage API
- Fetch API
- WebSocket (future feature)

## Performance Optimization

**Current Optimizations:**
- Code splitting via Vite
- Tree shaking for unused code
- Asset optimization (images, fonts)
- Lazy loading for large components

**Future Improvements:**
- Service worker for offline support
- Progressive Web App (PWA) capabilities
- Virtual scrolling for long lists
- Image lazy loading
- Component-level code splitting

## Future Enhancements

**Planned Features:**
- Real-time updates via WebSocket
- Notification system
- File upload support for documents
- Advanced search and filtering
- Dark/light theme toggle
- Multi-language support (i18n)
- Mobile application (React Native)

**UI/UX Improvements:**
- Drag-and-drop file upload
- Rich text editor for messages
- Emoji picker
- Markdown rendering
- Syntax highlighting for code blocks
- PDF preview in browser

## Resources

- **React Documentation**: https://react.dev
- **Vite Documentation**: https://vitejs.dev
- **Tailwind CSS**: https://tailwindcss.com
- **Axios**: https://axios-http.com

## Default Credentials

```
Super Admin:
  Email: admin@group9.com
  Password: admin123

Company Admin:
  Email: admin@crousemedical.com
  Password: admin123

Regular User:
  Email: user@crousemedical.com
  Password: password123
```

## License

Copyright 2025 FrontShiftAI. All rights reserved.