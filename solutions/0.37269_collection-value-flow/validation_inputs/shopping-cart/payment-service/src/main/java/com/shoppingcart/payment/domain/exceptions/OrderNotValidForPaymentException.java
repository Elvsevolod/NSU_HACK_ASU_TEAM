package com.shoppingcart.payment.domain.exceptions;

/**
 * Thrown when a payment is attempted for an order that is in a non-payable status.
 *
 * <p>Orders in {@code CANCELLED} or {@code PAID} status cannot receive new payments.
 * This check is performed by the
 * {@link com.shoppingcart.payment.framework.output.client.adapters.OrderClientAdapter}
 * during order validation.</p>
 */
public class OrderNotValidForPaymentException extends RuntimeException {

    /**
     * @param orderId the identifier of the order that is not eligible for payment
     * @param status  the current status of the order (e.g., "CANCELLED", "PAID")
     */
    public OrderNotValidForPaymentException(Long orderId, String status) {
        super("Order " + orderId + " is not valid for payment, current status: " + status);
    }
}
