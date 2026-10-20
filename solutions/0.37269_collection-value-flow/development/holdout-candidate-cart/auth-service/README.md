# Auth Service

Handles user registration and login. Issues JWT tokens signed with HS256 that are validated by other services (e.g. payment-service).

- **Port**: `8081`
- **Auth**: None — all endpoints are public
- **Database**: H2 in-memory (`authdb`)

## API Documentation

Swagger UI: http://localhost:8081/swagger-ui/index.html

## Architecture

Hexagonal (ports & adapters) with CQRS separation:

```
domain/          — User entity, value objects (Email, Password, Role), domain exceptions
application/
  command/       — RegisterUser and LoginUser use cases, input/output ports
  query/         — FindUser use case, input/output ports
framework/
  config/        — Spring Security, JWT service, password encoder adapter, bean wiring
  exceptions/    — Global exception handler
  input/         — REST controller and request/response DTOs
  output/        — JPA entity, repository, persistence adapter, mapper
```

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | Public | Register a new user, returns JWT |
| POST | `/api/auth/login` | Public | Authenticate user, returns JWT |

### Register

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secret123"
}
```

```json
HTTP 201 Created
{
  "token": "eyJhbGciOiJIUzI1NiJ9..."
}
```

### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secret123"
}
```

```json
HTTP 200 OK
{
  "token": "eyJhbGciOiJIUzI1NiJ9..."
}
```

## Error Responses

| HTTP | Error Code | Cause |
|------|-----------|-------|
| 400 | `INVALID_EMAIL` | Email format is invalid |
| 400 | `INVALID_PASSWORD` | Password does not meet requirements |
| 409 | `USER_ALREADY_EXISTS` | Email is already registered |
| 401 | `INVALID_CREDENTIALS` | Wrong email or password |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_PORT` | `8081` | Service port |
| `JWT_SECRET` | `miClaveSecretaMuyLarga1234567890AbcDef` | Signing secret — must match across all services that validate tokens |
| `JWT_EXPIRATION` | `86400000` | Token TTL in milliseconds (default 24 h) |
| `DB_USERNAME` | `sa` | H2 datasource username |
| `DB_PASSWORD` | _(empty)_ | H2 datasource password |

## JWT Shared Secret

The `JWT_SECRET` must be identical in every service that validates tokens (currently payment-service). Tokens are signed with **HS256**.

## H2 Console

Available at http://localhost:8081/h2-console

- **JDBC URL**: `jdbc:h2:mem:authdb`
- **Username**: `sa`
- **Password**: _(empty)_

## Running

```bash
mvn spring-boot:run
```
