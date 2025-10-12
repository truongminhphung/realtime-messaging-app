# 💬 Real-Time Messaging Application

A modern, scalable real-time messaging platform built with FastAPI, React, and a robust microservices architecture. This application demonstrates enterprise-level software engineering practices with containerization, automated CI/CD, and cloud deployment capabilities.

## 🚀 Features

- **Real-time messaging** with WebSocket connections
- **User authentication and authorization** with JWT tokens
- **Chat rooms and direct messaging** capabilities
- **Message persistence** with PostgreSQL
- **High-performance caching** with Redis
- **Asynchronous notifications** with RabbitMQ
- **Scalable architecture** ready for production deployment
- **Comprehensive testing** with automated CI/CD pipeline

## 🏗️ Architecture Overview

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend API** | FastAPI + Python 3.12 | REST API & WebSocket server |
| **Frontend** | React + JavaScript | User interface |
| **Database** | PostgreSQL 13 | Primary data storage |
| **Cache** | Redis 6 | Session management & caching |
| **Message Queue** | RabbitMQ 3 | Asynchronous task processing |
| **Package Manager** | uv | Fast Python dependency management |
| **Database Migrations** | Alembic | Schema version control |

### System Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frontend  │────│   Backend   │────│ PostgreSQL  │
│   (React)   │    │  (FastAPI)  │    │ (Database)  │
└─────────────┘    └─────────────┘    └─────────────┘
                           │                    │
                   ┌───────┴───────┐    ┌───────┴───────┐
                   │     Redis     │    │   RabbitMQ    │
                   │   (Cache)     │    │  (Queue)      │
                   └───────────────┘    └───────────────┘
```

## 📁 Project Structure

```
realtime-messaging-app/
├── backend/                 # FastAPI backend application
│   ├── app/
│   │   ├── models/         # SQLAlchemy database models
│   │   ├── routes/         # API route handlers
│   │   ├── services/       # Business logic services
│   │   ├── websocket/      # WebSocket handlers
│   │   └── migrations/     # Alembic database migrations
│   ├── tests/              # Backend test suite
│   └── pyproject.toml      # Python dependencies
├── frontend/               # React frontend application
│   ├── src/                # React source code
│   ├── public/             # Static assets
│   └── package.json        # Node.js dependencies
├── k8s/                    # Kubernetes deployment manifests
├── docker-compose.yml      # Local development environment
└── .github/workflows/      # CI/CD pipeline configuration
```

## 🛠️ Development Setup

### Prerequisites

- **Docker** & **Docker Compose** (for containerized development)
- **Python 3.12+** (for local backend development)
- **Node.js 18+** (for local frontend development)
- **Git** (for version control)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd realtime-messaging-app
   ```

2. **Start all services with Docker Compose**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development

#### Backend Development

```bash
# Navigate to backend directory
cd backend

# When adding new dependencies in pyproject.toml, run the following command to install them
uv sync

# Install dependencies using uv
uv sync --extra dev

# Set up environment variables
source env.sh

# Run database migrations
uv run alembic upgrade head

# Start development server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Development

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

#### Running Tests

```bash
# Backend tests
cd backend
uv run pytest --cov=app tests/

# Frontend tests
cd frontend
npm test
```

## 🗄️ Database Management

This project uses Alembic for database schema management:

```bash
# Create a new migration
cd backend
uv run alembic revision --autogenerate -m "Description of changes"

# Apply migrations
uv run alembic upgrade head

# Check current migration status
uv run alembic current

# View migration history
uv run alembic history
```

## 🚢 Deployment

### Docker Deployment

Build and run with Docker Compose:

```bash
# Production build
docker-compose -f docker-compose.yml up --build -d

# View logs
docker-compose logs -f
```

### Kubernetes Deployment

Deploy to Kubernetes cluster:

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods
kubectl get services
```

### AWS EKS Deployment

The application is configured for deployment to AWS EKS with:
- **ECR** for container image registry
- **EKS** for Kubernetes orchestration
- **RDS** for managed PostgreSQL
- **ElastiCache** for managed Redis
- **CloudWatch** for monitoring and logging

## 🔧 CI/CD Pipeline

The project includes a comprehensive GitHub Actions workflow:

- **Continuous Integration**
  - Automated testing for backend and frontend
  - Code coverage reporting
  - Security vulnerability scanning
  - Code quality checks

- **Continuous Deployment**
  - Automated Docker image building
  - Container registry publishing
  - Deployment to staging/production environments

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow Python PEP 8 style guide for backend code
- Use ESLint and Prettier for frontend code formatting
- Write comprehensive tests for new features
- Update documentation for API changes
- Ensure all CI checks pass before submitting PR

## 📝 API Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔒 Security

- JWT-based authentication
- Password hashing with bcrypt
- Input validation and sanitization
- CORS configuration
- Rate limiting with Redis

## 📊 Monitoring & Observability

- Application metrics with Prometheus
- Distributed tracing with OpenTelemetry
- Centralized logging with structured JSON logs
- Health checks for all services

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

For questions, issues, or contributions, please:
- Open an issue in the GitHub repository
- Check the documentation in the `/docs` directory
- Review existing issues and discussions

---

**Built with ❤️ using modern web technologies**

