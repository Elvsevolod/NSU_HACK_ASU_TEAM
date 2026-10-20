package com.shoppingcart.payment.domain.exceptions;

/**
 * Thrown when a payment is attempted for an order that already has an active
 * ({@code PENDING} or {@code APPROVED}) payment record.
 *
 * <p>Prevents duplicate payments for the same order by checking the repository
 * before creating a new {@link com.shoppingcart.payment.domain.entity.Payment}.</p>
 */
public class OrderAlreadyPaidException extends RuntimeException {

    /**
     * @param orderId the identifier of the order that already has an active payment
     */
    public OrderAlreadyPaidException(Long orderId) {
        super("Order " + orderId + " already has an active payment");
    }
}
