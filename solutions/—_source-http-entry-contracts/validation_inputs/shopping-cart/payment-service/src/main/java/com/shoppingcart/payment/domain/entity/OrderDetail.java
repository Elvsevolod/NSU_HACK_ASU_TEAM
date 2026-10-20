package com.shoppingcart.payment.domain.entity;

import java.math.BigDecimal;

/**
 * Read-only snapshot of an order line item within the payment bounded context.
 *
 * <p>This entity is not managed or persisted by the payment service. It represents the
 * product line-item data that may be carried in order validation responses from the
 * order-service. Instances are immutable once created.</p>
 */
public class OrderDetail {

    private final Long id;
    private final Long productId;
    private final String productName;
    private final Integer quantity;
    private final BigDecimal unitPrice;

    private OrderDetail(Long id, Long productId, String productName, Integer quantity, BigDecimal unitPrice) {
        this.id = id;
        this.productId = productId;
        this.productName = productName;
        this.quantity = quantity;
        this.unitPrice = unitPrice;
    }

    /**
     * Reconstitutes an {@code OrderDetail} from external data (e.g., order-service response).
     *
     * @param id          the line-item identifier
     * @param productId   the product identifier
     * @param productName the product name at the time the order was placed
     * @param quantity    the number of units ordered
     * @param unitPrice   the price per unit
     * @return a fully populated {@code OrderDetail} instance
     */
    public static OrderDetail reconstitute(Long id, Long productId, String productName,
            Integer quantity, BigDecimal unitPrice) {
        return new OrderDetail(id, productId, productName, quantity, unitPrice);
    }

    public Long getId() { return id; }
    public Long getProductId() { return productId; }
    public String getProductName() { return productName; }
    public Integer getQuantity() { return quantity; }
    public BigDecimal getUnitPrice() { return unitPrice; }
}
