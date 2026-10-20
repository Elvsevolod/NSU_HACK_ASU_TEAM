package com.shoppingcart.order.domain.exceptions;

import com.shoppingcart.order.domain.vo.OrderId;

/**
 * Thrown when an order cannot be located in the repository for a given identifier.
 *
 * <p>Use cases that load an order by ID (e.g., confirm, cancel, retrieve) raise this
 * exception when no matching record exists, signalling a not-found condition that
 * upper layers can map to an appropriate HTTP 404 response.</p>
 */
public class OrderNotFoundException extends RuntimeException {

    /**
     * Creates the exception identifying the missing order.
     *
     * @param id the identifier for which no order was found
     */
    public OrderNotFoundException(OrderId id) {
        super("Order not found with id: " + id.value());
    }
}
