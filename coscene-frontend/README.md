# CoScene Frontend

React-based web interface for the CoScene agentic 3D scene editing system.

## Features

- **Chat Interface** - Natural language scene editing using assistant-ui
- **3D Viewport** - Real-time Three.js scene rendering
- **Live Updates** - Scene updates as you edit
- **Fixed Split Layout** - Chat (40%) | 3D Viewer (60%)

## Tech Stack

- **React 18** with TypeScript
- **assistant-ui** - Chat interface with LocalRuntime
- **Three.js** - 3D rendering (vanilla, no react-three/fiber)
- **Tailwind CSS** - Styling
- **Vite** - Build tool

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- CoScene backend running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env
```

### Configuration

Edit `.env` to match your backend:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_DEFAULT_USER_ID=00000000-0000-0000-0000-000000000001
```

### Run Development Server

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

## Project Structure

```
src/
├── components/
│   ├── ChatPanel/          # Chat interface components
│   │   ├── ChatPanel.tsx   # Main chat container
│   │   └── CustomMessage.tsx # Message rendering with renders
│   ├── SceneViewer/        # Three.js 3D viewer
│   │   └── SceneViewer.tsx # Scene rendering component
│   └── Layout/             # Layout components
│       ├── AppLayout.tsx   # Main split layout
│       └── Header.tsx      # App header
├── services/
│   ├── api.ts              # REST API client
│   └── runtime.ts          # assistant-ui runtime setup
├── hooks/
│   ├── useSession.ts       # Session management
│   └── useSceneLoader.ts   # USD scene loading
├── types/
│   ├── api.types.ts        # API response types
│   ├── scene.types.ts      # 3D scene types
│   └── message.types.ts    # WebSocket message types (Phase 2)
├── utils/
│   └── usdLoader.ts        # USD parsing utility
└── App.tsx                 # Main app component
```

## Usage

1. **Start a session** - Automatically created on page load
2. **Type a prompt** - e.g., "Create a red sphere in the center"
3. **View the result** - Scene updates in the 3D viewport
4. **Continue editing** - Chat maintains conversation context

### Example Prompts

- "Create a blue cube"
- "Add a yellow sphere above the cube"
- "Make the cube larger"
- "Change the sphere color to green"
- "Add three objects in a row"

## Development

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Troubleshooting

### Backend Connection Issues

If you see "Failed to Create Session":
1. Ensure backend is running: `cd ../coscene-backend && docker-compose up`
2. Check API URL in `.env` matches backend port
3. Verify CORS is enabled in backend

### Scene Not Loading

If the 3D viewer shows errors:
1. Check browser console for USD parsing errors
2. Verify backend is returning valid USD content
3. Try a simple prompt like "Create a sphere"
