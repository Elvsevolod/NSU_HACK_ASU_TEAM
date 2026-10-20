package com.shoppingcart.order.domain.exceptions;

import com.shoppingcart.order.domain.vo.OrderId;

/**
 * Thrown when an attempt is made to cancel an order that has already been cancelled.
 *
 * <p>Cancellation is a terminal state transition; calling
 * {@link com.shoppingcart.order.domain.entity.Order#cancel()} on an order that is
 * already in {@code CANCELLED} status violates the domain invariant and triggers this exception.</p>
 */
public class OrderAlreadyCancelledException extends RuntimeException {

    /**
     * Creates the exception identifying the already-cancelled order.
     *
     * @param id the identifier of the order that has already been cancelled
     */
    public OrderAlreadyCancelledException(OrderId id) {
        super("Order with id " + id.value() + " has already been cancelled");
    }
}
