package com.shoppingcart.payment.domain.exceptions;


/**
 * Thrown when a payment amount is invalid — either non-positive or inconsistent with the order total.
 *
 * <p>This exception covers two distinct scenarios:</p>
 * <ul>
 *   <li>The client supplies a zero or negative amount (caught at domain creation time).</li>
 *   <li>The client-supplied amount does not match the authoritative total from the order-service.</li>
 * </ul>
 */
public class InvalidPaymentAmountException extends RuntimeException {

    /**
     * Used when the payment amount is zero or negative.
     */
    public InvalidPaymentAmountException() {
        super("Payment amount must be greater than zero");
    }

    /**
     * Used when the payment amount does not match the order's total.
     *
     * @param expected the order total as returned by the order-service
     * @param received the amount supplied by the client
     */
    public InvalidPaymentAmountException(java.math.BigDecimal expected, java.math.BigDecimal received) {
        super("Payment amount " + received + " does not match order total " + expected);
    }
}
