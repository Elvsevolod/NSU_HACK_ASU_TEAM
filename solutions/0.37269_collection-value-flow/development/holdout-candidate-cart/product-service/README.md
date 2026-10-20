# Product Service

Proxy microservice to [FakeStore API](https://fakestoreapi.com). Exposes product data needed by the shopping cart — specifically used by the order-service to validate product prices before an order is created.

- **Port**: `8080`
- **Auth**: None — all endpoints are public
- **External dependency**: [FakeStore API](https://fakestoreapi.com)

## API Documentation

Swagger UI: http://localhost:8080/swagger-ui/index.html

## Architecture

Hexagonal (ports & adapters):

```
domain/          — Product entity and value objects (ProductId, Money, Category, ProductImage)
application/
  query/         — GetProduct, ListProducts, ListProductsByCategory use cases and ports
framework/
  config/        — Spring config and bean wiring
  exceptions/    — Global exception handler
  input/         — REST controller and response DTO
  output/        — FakeStore HTTP client adapter and mapper
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/products` | List all products |
| GET | `/api/products/{id}` | Get product by ID |
| GET | `/api/products/category/{category}` | List products by category |

### Examples

```bash
# List all products
curl http://localhost:8080/api/products

# Get product by ID
curl http://localhost:8080/api/products/1

# List by category
curl http://localhost:8080/api/products/category/electronics
```

## Error Responses

| HTTP | Error Code | Cause |
|------|-----------|-------|
| 404 | `PRODUCT_NOT_FOUND` | Product does not exist in FakeStore |
| 400 | `INVALID_DATA` | Invalid product data from upstream |
| 500 | `INTERNAL_ERROR` | Unexpected error |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_PORT` | `8080` | Service port |
| `FAKESTORE_BASE_URL` | `https://fakestoreapi.com` | FakeStore API base URL |

## Running

```bash
mvn spring-boot:run
```
