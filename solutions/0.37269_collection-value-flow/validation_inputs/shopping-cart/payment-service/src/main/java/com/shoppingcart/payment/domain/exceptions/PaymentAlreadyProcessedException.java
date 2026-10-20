package com.shoppingcart.payment.domain.exceptions;


/**
 * Thrown when a state transition is attempted on a payment that has already left
 * {@code PENDING} status (for approve/reject) or is not in {@code APPROVED} status (for refund).
 *
 * <p>Enforces the domain invariant that each lifecycle transition can only occur once,
 * preventing double-approvals, double-rejections, or refunds of non-approved payments.</p>
 */
public class PaymentAlreadyProcessedException extends RuntimeException {

    /**
     * @param id the identifier of the payment that has already been processed
     */
    public PaymentAlreadyProcessedException(Long id) {
        super("Payment " + id + " has already been processed");
    }
}

