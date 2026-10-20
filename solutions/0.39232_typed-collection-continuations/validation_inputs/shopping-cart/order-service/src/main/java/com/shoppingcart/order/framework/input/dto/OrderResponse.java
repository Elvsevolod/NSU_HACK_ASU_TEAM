package com.shoppingcart.order.framework.input.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/**
 * HTTP response body representing an order returned by the REST API.
 *
 * <p>Produced by {@link com.shoppingcart.order.framework.input.mapper.OrderHttpMapper#toResponse(com.shoppingcart.order.domain.entity.Order)}
 * from a domain {@link com.shoppingcart.order.domain.entity.Order} aggregate. It is a flat,
 * serialization-friendly projection of the domain model, decoupled from persistence concerns.</p>
 *
 * @param id            the unique identifier of the order
 * @param customerId    the identifier of the customer who placed the order
 * @param customerName  the full name of the customer at the time the order was placed
 * @param customerEmail the e-mail address of the customer at the time the order was placed
 * @param status        the current lifecycle status of the order (e.g., "PENDING", "PAID")
 * @param createdAt     the timestamp when the order was originally created
 * @param total         the sum of all line-item subtotals
 * @param details       the list of product line items included in the order
 */
public record OrderResponse(
        Long id,
        Long customerId,
        String customerName,
        String customerEmail,
        String status,
        LocalDateTime createdAt,
        BigDecimal total,
        List<OrderDetailResponse> details
) {
    /**
     * Nested response object representing a single product line item within the order.
     *
     * @param id          the unique identifier of this line item
     * @param productId   the identifier of the product in the catalog
     * @param productName the name of the product at the time the order was placed
     * @param quantity    the number of units ordered
     * @param unitPrice   the price per unit recorded at order creation time
     * @param subtotal    the computed subtotal ({@code unitPrice × quantity})
     */
    public record OrderDetailResponse(
            Long id,
            Long productId,
            String productName,
            int quantity,
            BigDecimal unitPrice,
            BigDecimal subtotal
    ) {}
}
