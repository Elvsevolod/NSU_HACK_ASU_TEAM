package com.shoppingcart.order.domain.vo;

/**
 * Value object representing the unique identifier of an {@link com.shoppingcart.order.domain.entity.Order}.
 *
 * <p>A {@code null} value is allowed to represent an order that has not yet been persisted
 * (i.e., a newly created order without a database-assigned ID). Once set, the value must
 * be a positive number.</p>
 *
 * @param value the numeric identifier, or {@code null} for transient orders
 */
public record OrderId(Long value) {

    /**
     * Compact canonical constructor that validates the identifier.
     *
     * @throws IllegalArgumentException if {@code value} is non-null and not a positive number
     */
    public OrderId {
        if (value != null && value <= 0)
            throw new IllegalArgumentException("OrderId must be a positive number");
    }
}
