# SmartERP - Enterprise Resource Planning System

A comprehensive, production-grade Enterprise Resource Planning system built with Django, Django REST Framework, React, PostgreSQL, Redis, and Celery. Designed with multi-tenant architecture to serve multiple organizations from a single deployment.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Modules](#modules)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Overview

SmartERP provides a unified platform for managing core business processes across multiple departments. It supports multi-tenant isolation, role-based access control, and real-time data processing.

### Key Features

- **Multi-Tenant Architecture**: Full data isolation per organization using schema-level or row-level tenancy.
- **Role-Based Access Control**: Granular permissions system with customizable roles per module.
- **Real-Time Processing**: Celery-powered background task processing for payroll, reports, and notifications.
- **RESTful API**: Fully documented API endpoints with token-based authentication.
- **Responsive Dashboard**: React-based frontend with real-time KPI tracking and interactive charts.

## Architecture

```
                    +-------------------+
                    |   Nginx (Proxy)   |
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+       +-----------v-----------+
    |  React Frontend   |       |   Django Backend      |
    |  (Port 3000)      |       |   (Port 8000)         |
    +-------------------+       +-----+-----+-----------+
                                      |     |
                          +-----------+     +----------+
                          |                            |
                +---------v--------+       +-----------v------+
                |   PostgreSQL     |       |   Redis          |
                |   (Port 5432)    |       |   (Port 6379)    |
                +------------------+       +--------+---------+
                                                    |
                                           +--------v---------+
                                           |   Celery Worker   |
                                           |   Celery Beat     |
                                           +-------------------+
```

## Modules

### Human Resources (HR)
- Employee management and profiles
- Position and department tracking
- Leave request workflow with approval chain
- Attendance tracking and reporting
- Payroll processing with automated calculations

### Finance
- Chart of accounts management
- Transaction recording (debits/credits)
- Invoice generation and tracking
- Budget planning and monitoring
- Expense management and approval

### Inventory
- Multi-warehouse management
- Product catalog with categories and SKUs
- Stock movement tracking (inbound/outbound/transfer)
- Real-time stock level monitoring
- Low stock alerts and reorder points

### Procurement
- Supplier management
- Purchase request workflow
- Purchase order creation and tracking
- Goods receipt processing
- Supplier performance evaluation

### Sales
- Customer relationship management
- Quotation generation
- Sales order processing
- Revenue tracking and reporting
- Sales pipeline analytics

### Project Management
- Project lifecycle management
- Task assignment and tracking
- Milestone planning
- Time entry and billable hours
- Project budget tracking

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Backend     | Django 5.0, Django REST Framework   |
| Frontend    | React 18, Redux Toolkit, Chart.js   |
| Database    | PostgreSQL 16                       |
| Cache/Queue | Redis 7                             |
| Task Queue  | Celery 5                            |
| Proxy       | Nginx                               |
| Container   | Docker, Docker Compose              |

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/smarterp.git
   cd smarterp
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**
   ```bash
   docker-compose up --build
   ```

4. **Run database migrations**
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

5. **Create a superuser**
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

6. **Access the application**
   - Frontend: http://localhost
   - Backend API: http://localhost/api/
   - Admin Panel: http://localhost/admin/
   - API Documentation: http://localhost/api/docs/

### Development Setup (without Docker)

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

#### Frontend
```bash
cd frontend
npm install
npm start
```

## Configuration

### Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DJANGO_SECRET_KEY`: Django secret key for cryptographic signing
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `DJANGO_SETTINGS_MODULE`: Settings module (development/production)

## API Documentation

Once the application is running, interactive API documentation is available at:
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`

### Authentication

The API uses JWT (JSON Web Token) authentication. Obtain tokens via:

```
POST /api/v1/accounts/login/
{
    "email": "user@example.com",
    "password": "your_password"
}
```

Include the token in subsequent requests:
```
Authorization: Bearer <access_token>
```

## Deployment

### Production Deployment

1. Set `DJANGO_SETTINGS_MODULE=config.settings.production`
2. Configure a strong `DJANGO_SECRET_KEY`
3. Set `DJANGO_ALLOWED_HOSTS` to your domain
4. Enable HTTPS via Nginx configuration
5. Configure proper database credentials
6. Set up monitoring and logging

### Scaling

- **Horizontal scaling**: Add more Celery workers for background tasks
- **Database**: Configure PostgreSQL read replicas for read-heavy workloads
- **Caching**: Redis caching is built-in for frequently accessed data
- **Static files**: Serve via CDN in production

## Testing

```bash
# Run backend tests
docker-compose exec backend python manage.py test

# Run with coverage
docker-compose exec backend coverage run manage.py test
docker-compose exec backend coverage report

# Run frontend tests
docker-compose exec frontend npm test
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Create a Pull Request

### Code Standards

- Backend: Follow PEP 8, use `flake8` and `black` for formatting
- Frontend: Follow ESLint configuration, use Prettier for formatting
- Write tests for all new features
- Update documentation as needed

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
