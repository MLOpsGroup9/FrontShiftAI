# FrontShiftAI - Frontend

A modern AI dashboard web application built with React, Vite, and Tailwind CSS, featuring a glassmorphism design inspired by Axora AI.

## Features

- 🎨 **Glassmorphism UI** - Modern, dark theme with frosted glass effects
- 💬 **RAG-powered Chat** - Integrated with backend RAG API for intelligent responses
- 🌈 **Smooth Animations** - Floating orbs, gradients, and transitions
- 📱 **Responsive Design** - Clean, minimalistic interface
- 🔌 **API Integration** - Connected to FastAPI backend

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Axios** - HTTP client for API calls

## Setup

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure API URL (optional):**
   Create a `.env` file in the `frontend` directory:
   ```
   VITE_API_URL=http://localhost:8001
   ```
   If not set, it defaults to `http://localhost:8001`

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Build for production:**
   ```bash
   npm run build
   ```

5. **Preview production build:**
   ```bash
   npm run preview
   ```

## Backend Connection

The frontend connects to the FastAPI backend running on port 8001 by default. Make sure the backend API is running before using the chat feature.

### API Endpoints Used:
- `GET /health` - Health check
- `POST /api/rag/query` - RAG query endpoint

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Sidebar.jsx       # Left sidebar with navigation
│   │   ├── ChatArea.jsx      # Main chat display area
│   │   └── MessageInput.jsx  # Message input component
│   ├── services/
│   │   └── api.js            # API service functions
│   ├── App.jsx               # Main app component
│   ├── main.jsx              # Entry point
│   └── index.css             # Global styles
├── index.html
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## Development

The app runs on `http://localhost:3000` by default. Vite provides hot module replacement (HMR) for fast development.

## Environment Variables

- `VITE_API_URL` - Backend API URL (default: `http://localhost:8001`)

## Notes

- The app requires the backend API to be running for full functionality
- CORS is configured in the backend to allow requests from `http://localhost:3000`
- The UI uses glassmorphism effects with Tailwind CSS utilities
