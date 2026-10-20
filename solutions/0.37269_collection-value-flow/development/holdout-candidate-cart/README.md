# Shopping Cart Microservices

A shopping cart system built with Spring Boot following hexagonal architecture across four independent microservices.

## Services

| Service | Port | Description |
|---------|------|-------------|
| [product-service](./product-service) | 8080 | Proxy to FakeStore API — product catalog |
| [auth-service](./auth-service) | 8081 | User registration and login — issues JWT tokens |
| [payment-service](./payment-service) | 8082 | Payment simulation with order validation (JWT protected) |
| [order-service](./order-service) | 8083 | Order lifecycle management |

## API Documentation

Each service exposes interactive API docs via Swagger UI once running:

| Service | Swagger UI |
|---------|-----------|
| product-service | http://localhost:8080/swagger-ui/index.html |
| auth-service | http://localhost:8081/swagger-ui/index.html |
| payment-service | http://localhost:8082/swagger-ui/index.html |
| order-service | http://localhost:8083/swagger-ui/index.html |

## Architecture

Each service follows **Hexagonal Architecture (Ports & Adapters)** with CQRS separation:

```
domain/         ← Entities, value objects, domain exceptions (no framework dependencies)
application/
  command/      ← Write use cases, input/output ports
  query/        ← Read use cases, input/output ports
framework/
  config/       ← Spring config, bean wiring, security
  exceptions/   ← Global exception handler
  input/        ← REST controllers, request/response DTOs
  output/       ← JPA adapters, HTTP clients, mappers
```

## Service Communication

```
auth-service (8081)
        │ issues JWT
        ↓
payment-service (8082) — validates JWT on every request
        │
        │ 1. validates order state   GET  /api/orders/{id}
        │ 2. marks order paid        PATCH /api/orders/{id}/pay
        │ 3. reverts on refund       PATCH /api/orders/{id}/revert-payment
        ↓
order-service (8083)
        │
        │ validates products on creation
        ↓
product-service (8080) → FakeStore API (external)
```

## Running Locally

Start services in this order (each has default values — no extra config needed):

```bash
# Terminal 1 — no dependencies
cd product-service && mvn spring-boot:run

# Terminal 2 — no dependencies
cd auth-service && mvn spring-boot:run

# Terminal 3 — depends on product-service
cd order-service && mvn spring-boot:run

# Terminal 4 — depends on order-service and auth-service
cd payment-service && mvn spring-boot:run
```

> All environment variables have sensible defaults. The `JWT_SECRET` defaults to the same value across services so tokens work out of the box locally.

## H2 Consoles (development)

| Service | URL | JDBC URL |
|---------|-----|----------|
| auth-service | http://localhost:8081/h2-console | `jdbc:h2:mem:authdb` |
| order-service | http://localhost:8083/h2-console | `jdbc:h2:mem:orderdb` |
| payment-service | http://localhost:8082/h2-console | `jdbc:h2:mem:paymentdb` |

## Tech Stack

- Java 21
- Spring Boot 4.0.6
- Spring Security + JJWT (auth-service, payment-service)
- Spring Data JPA + H2
- OpenFeign (product-service)
- RestTemplate (order-service, payment-service)
- Lombok
- SpringDoc OpenAPI (Swagger UI)
