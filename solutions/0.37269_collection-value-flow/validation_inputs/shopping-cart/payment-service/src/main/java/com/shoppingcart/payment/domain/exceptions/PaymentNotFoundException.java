package com.shoppingcart.payment.domain.exceptions;

/**
 * Thrown when a payment cannot be located in the repository for a given identifier.
 *
 * <p>Raised by the persistence adapter when no record exists for the requested ID,
 * signalling a not-found condition that upper layers map to an HTTP 404 response.</p>
 */
public class PaymentNotFoundException extends RuntimeException {

    /**
     * @param id the identifier for which no payment was found
     */
    public PaymentNotFoundException(Long id) {
        super("Payment with ID " + id + " not found");
    }
}
