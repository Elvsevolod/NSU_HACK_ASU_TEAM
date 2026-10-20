package com.shoppingcart.order.domain.exceptions;

/**
 * Thrown when the price of a product provided by the client does not match
 * the price returned by the product catalog at the time of order creation.
 *
 * <p>This exception enforces price integrity: the domain rejects any order whose
 * client-supplied price deviates from the authoritative catalog price, preventing
 * price-manipulation attacks or stale client data from corrupting order totals.</p>
 */
public class PriceMismatchException extends RuntimeException {

    /**
     * Creates the exception with a detailed message including the product ID and both prices.
     *
     * @param productId     the ID of the product whose price does not match
     * @param expectedPrice the price the client sent
     * @param actualPrice   the price returned by the product catalog
     */
    public PriceMismatchException(Long productId, Double expectedPrice, Double actualPrice) {
        super("Price mismatch for product " + productId + ". Expected: " + expectedPrice + ", Actual: " + actualPrice);
    }

    /**
     * Creates the exception with a custom message.
     *
     * @param message a human-readable description of the price mismatch
     */
    public PriceMismatchException(String message) {
        super(message);
    }
}
