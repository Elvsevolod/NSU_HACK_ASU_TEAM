# Order Service

Manages the full order lifecycle: creation, cancellation, payment marking, and payment reversion. Validates product prices against the product-service before persisting a new order.

- **Port**: `8083`
- **Auth**: None — all endpoints are public
- **Database**: H2 in-memory (`orderdb`)
- **Dependencies**: product-service (for price validation on order creation)

## API Documentation

Swagger UI: http://localhost:8083/swagger-ui/index.html

## Architecture

Hexagonal (ports & adapters) with CQRS separation:

```
domain/          — Order, Customer, OrderDetail entities; value objects (OrderId, Quantity, OrderStatus); domain exceptions
application/
  command/       — CreateOrder, CancelOrder, MarkOrderAsPaid, RevertOrderToPending use cases and ports
  query/         — GetOrder, ListOrdersByCustomer use cases and ports
framework/
  config/        — Spring config and bean wiring
  exceptions/    — Global exception handler
  input/         — REST controller and request/response DTOs
  output/        — JPA entities, repository, persistence adapter, HTTP client to product-service
```

## Endpoints

| Method | Path | Caller | Description |
|--------|------|--------|-------------|
| POST | `/api/orders` | Client | Create a new order |
| GET | `/api/orders/{id}` | Client / payment-service | Get order by ID |
| GET | `/api/orders?customerId={id}` | Client | List orders by customer |
| PATCH | `/api/orders/{id}/cancel` | Client | Cancel an order |
| PATCH | `/api/orders/{id}/pay` | payment-service | Mark order as paid |
| PATCH | `/api/orders/{id}/revert-payment` | payment-service | Revert paid order back to pending |

### Order Status Flow

```
PENDING → CONFIRMED → PAID
PENDING → CANCELLED
CONFIRMED → CANCELLED
PAID → PENDING  (revert-payment)
```

### Create Order

```http
POST /api/orders
Content-Type: application/json

{
  "customerId": 1,
  "customerName": "John Doe",
  "customerEmail": "john@example.com",
  "details": [
    {
      "productId": 1,
      "productName": "Fjallraven - Foldsack No. 1 Backpack",
      "quantity": 2,
      "unitPrice": 109.95
    }
  ]
}
```

```json
HTTP 201 Created
{
  "id": 1,
  "customerId": 1,
  "customerName": "John Doe",
  "customerEmail": "john@example.com",
  "status": "PENDING",
  "createdAt": "2025-05-06T10:00:00",
  "total": 219.90,
  "details": [...]
}
```

> The `unitPrice` is validated against the product-service catalog. The request is rejected with `409 PRICE_MISMATCH` if the prices differ.

## Error Responses

| HTTP | Error Code | Cause |
|------|-----------|-------|
| 404 | `ORDER_NOT_FOUND` | No order found for the given ID |
| 409 | `ORDER_ALREADY_CANCELLED` | Cannot cancel an already-cancelled order |
| 409 | `PRICE_MISMATCH` | Client price does not match the catalog |
| 400 | `INVALID_PRODUCT` | Product does not exist or is unavailable |
| 400 | `INVALID_ARGUMENT` | Empty order details or invalid values |
| 400 | `VALIDATION_ERROR` | Request body failed Bean Validation |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_PORT` | `8083` | Service port |
| `PRODUCT_SERVICE_URL` | `http://localhost:8080/api/products` | Product-service base URL |
| `DB_USERNAME` | `sa` | H2 datasource username |
| `DB_PASSWORD` | _(empty)_ | H2 datasource password |

## H2 Console

Available at http://localhost:8083/h2-console

- **JDBC URL**: `jdbc:h2:mem:orderdb`
- **Username**: `sa`
- **Password**: _(empty)_

## Running

```bash
mvn spring-boot:run
```
