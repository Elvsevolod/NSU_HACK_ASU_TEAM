# Payment Service

Simulates payment processing. Validates that the referenced order exists and is in a payable state, then records the payment and notifies the order-service to update the order status. Supports refunds that revert the order back to `PENDING`.

- **Port**: `8082`
- **Auth**: JWT required — obtain a token from auth-service first
- **Database**: H2 in-memory (`paymentdb`)
- **Dependencies**: order-service (order validation and status updates)

## API Documentation

Swagger UI: http://localhost:8082/swagger-ui/index.html

## Architecture

Hexagonal (ports & adapters) with CQRS separation:

```
domain/          — Payment entity, value objects (PaymentStatus, PaymentMethod), Customer and OrderDetail snapshot entities, domain exceptions
application/
  command/       — ProcessPayment and RefundPayment use cases, input/output ports
  query/         — GetPayment, GetPaymentsByOrder use cases and ports
framework/
  config/        — Spring Security, JWT validation filter, bean wiring
  exceptions/    — Global exception handler
  input/         — REST controller and request/response DTOs
  output/        — JPA entity, repository, persistence adapter, HTTP client to order-service
```

## Authentication

All endpoints require a valid JWT in the `Authorization` header:

```http
Authorization: Bearer <token>
```

Obtain a token from **auth-service** (`POST /api/auth/login`). The `JWT_SECRET` must match between both services.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/payments` | Process a payment for an order |
| PATCH | `/api/payments/{id}/refund` | Refund a payment |
| GET | `/api/payments/{id}` | Get payment by ID |
| GET | `/api/payments?orderId={id}` | List all payments for an order |

### Process Payment

```http
POST /api/payments
Authorization: Bearer <token>
Content-Type: application/json

{
  "orderId": 1,
  "customerId": 1,
  "amount": 219.90,
  "paymentMethod": "CREDIT_CARD"
}
```

```json
HTTP 201 Created
{
  "id": 1,
  "orderId": 1,
  "status": "APPROVED",
  "paymentMethod": "CREDIT_CARD",
  "amount": 219.90,
  "processedAt": "2025-05-06T10:05:00"
}
```

### Refund Payment

```http
PATCH /api/payments/1/refund
Authorization: Bearer <token>
```

```json
HTTP 200 OK
{
  "id": 1,
  "orderId": 1,
  "status": "REFUNDED",
  ...
}
```

### Available Payment Methods

`CREDIT_CARD` · `DEBIT_CARD` · `PAYPAL` · `BANK_TRANSFER`

## Payment Flow

```
Client → POST /api/payments
          │
          ├─ validate order exists and is PENDING/CONFIRMED  (GET order-service)
          ├─ simulate payment processing
          ├─ persist payment with APPROVED status
          └─ notify order-service                            (PATCH /api/orders/{id}/pay)

Client → PATCH /api/payments/{id}/refund
          │
          ├─ mark payment as REFUNDED
          └─ notify order-service                            (PATCH /api/orders/{id}/revert-payment)
```

## Error Responses

| HTTP | Error Code | Cause |
|------|-----------|-------|
| 401 | — | Missing or invalid JWT |
| 404 | `PAYMENT_NOT_FOUND` | No payment found for the given ID |
| 404 | `ORDER_NOT_FOUND` | The referenced order does not exist |
| 409 | `ORDER_ALREADY_PAID` | Order has already been paid |
| 409 | `ORDER_NOT_VALID_FOR_PAYMENT` | Order is not in a payable state |
| 409 | `PAYMENT_ALREADY_PROCESSED` | Payment has already been processed |
| 400 | `INVALID_PAYMENT_AMOUNT` | Amount is zero or negative |
| 400 | `VALIDATION_ERROR` | Request body failed Bean Validation |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_PORT` | `8082` | Service port |
| `ORDER_SERVICE_URL` | `http://localhost:8083/api/orders` | Order-service base URL |
| `JWT_SECRET` | `miClaveSecretaMuyLarga1234567890AbcDef` | Must match auth-service secret |
| `DB_USERNAME` | `sa` | H2 datasource username |
| `DB_PASSWORD` | _(empty)_ | H2 datasource password |

## H2 Console

Available at http://localhost:8082/h2-console

- **JDBC URL**: `jdbc:h2:mem:paymentdb`
- **Username**: `sa`
- **Password**: _(empty)_

## Running

```bash
mvn spring-boot:run
```

> Requires **order-service** and **auth-service** to be running first.
