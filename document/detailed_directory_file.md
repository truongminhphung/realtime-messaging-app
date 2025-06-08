# Project Structure Documentation

## CI/CD Pipeline

### `.github/workflows/ci.yml`
Defines the **Continuous Integration pipeline** using GitHub Actions:
- Builds Docker images for backend and frontend
- Runs automated tests using pytest
- Pushes images to AWS ECR (Elastic Container Registry)
- **Trigger**: Push or pull requests to `main` branch

### `.github/workflows/cd.yml`
Defines the **Continuous Deployment pipeline**:
- Deploys applications to AWS EKS (Elastic Kubernetes Service)
- Updates Kubernetes manifests with new image tags
- **Trigger**: After successful CI pipeline completion

## Application Directories

### `backend/`
Contains the **monolithic FastAPI application** with:
- REST API endpoints
- WebSocket event handling
- RabbitMQ worker logic for background tasks

### `frontend/`
Contains the **React frontend application**:
- Served via Nginx in production environment
- Handles user interface and client-side logic

### `k8s/`
**Kubernetes manifests** for deploying services to AWS EKS:
- Deployment configurations
- Service definitions
- Ingress rules
- Secrets management

## Configuration Files

### `.gitignore`
Excludes unnecessary files from version control:
- `__pycache__/` (Python cache files)
- `node_modules/` (Node.js dependencies)
- `.env` (environment variables)
- `*.log` (log files)

### `docker-compose.yml`
Defines services for **local development and testing**:
- Backend (FastAPI)
- Frontend (React)
- PostgreSQL database
- Redis cache
- RabbitMQ message broker

### `README.md`
Project documentation including:
- Setup instructions
- Installation guide
- Usage instructions

## Backend Structure (`app/`)

### Core Files
- **`dependencies.py`**: FastAPI dependencies (database session, JWT validation)
- **`config.py`**: Environment variable loader (DATABASE_URL, REDIS_URL, RABBITMQ_URL)
- **`main.py`**: FastAPI application entry point with middleware and route mounting

### Services Directory (`app/services/`)
Business logic and external service integrations:

- **`__init__.py`**: Empty package marker
- **`database.py`**: SQLAlchemy session management
- **`redis.py`**: Redis client for caching and rate limiting
- **`rabbitmq.py`**: RabbitMQ client for task publishing
- **`auth.py`**: JWT token generation and validation
- **`notification_worker.py`**: RabbitMQ task consumer for email notifications

## Frontend Structure (`frontend/`)

### Public Assets
- **`public/index.html`**: HTML entry point for React application

### Source Code (`src/`)
- **`App.js`**: Main React component with routing (Login, Register, Room, etc.)
- **`index.js`**: React application renderer

### Components (`src/components/`)
Reusable UI components:
- **`Login.js`**: Login form with email/password fields
- **`Register.js`**: User registration form
- **`RoomList.js`**: Displays user's chat rooms
- **`Room.js`**: Chat room interface with message input
- **`MessageList.js`**: Message display component
- **`NotificationList.js`**: Notification display component

### Custom Hooks (`src/hooks/`)
State management hooks:
- **`useAuth.js`**: JWT and user state management
- **`useWebSocket.js`**: WebSocket connection handling

### Utilities (`src/utils/`)
Helper functions:
- **`api.js`**: Axios client for REST API calls
- **`websocket.js`**: WebSocket client for `/ws/{room_id}` connections

### Testing (`tests/`)
Jest and React Testing Library tests:
- **`App.test.js`**: Application component tests
- **`Login.test.js`**: Login component tests
- Additional component test files

### Build Configuration
- **`Dockerfile`**: Builds and serves React application

## Kubernetes Configuration (`k8s/`)

### Deployment Files
- **`backend-deployment.yaml`**: FastAPI backend deployment (2 replicas with worker logic)
- **`frontend-deployment.yaml`**: React frontend deployment (2 replicas)
- **`rabbitmq-deployment.yaml`**: RabbitMQ deployment (Bitnami Helm chart or custom)

### Networking & Security
- **`nginx-ingress.yaml`**: Nginx Ingress controller configuration for request routing
- **`secrets.yaml`**: Base64-encoded sensitive configuration (URLs, credentials)