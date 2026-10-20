package com.shoppingcart.order.domain.vo;

/**
 * Value object representing the quantity of a product in an
 * {@link com.shoppingcart.order.domain.entity.OrderDetail}.
 *
 * <p>Enforces the invariant that a quantity must always be a strictly positive integer,
 * preventing zero or negative amounts from entering the domain model.</p>
 *
 * @param value the number of units, must be greater than zero
 */
public record Quantity(int value) {

    /**
     * Compact canonical constructor that validates the quantity.
     *
     * @throws IllegalArgumentException if {@code value} is zero or negative
     */
    public Quantity {
        if (value <= 0)
            throw new IllegalArgumentException("Quantity must be greater than zero");
    }
}