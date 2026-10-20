package com.shoppingcart.order.domain.exceptions;

/**
 * Thrown when a product referenced in an order cannot be found in the catalog or is unavailable.
 *
 * <p>This exception is raised during order creation when the product service indicates that
 * a requested product does not exist, has been discontinued, or is otherwise not eligible
 * for purchase.</p>
 */
public class InvalidProductException extends RuntimeException {

    /**
     * Creates the exception with a custom message.
     *
     * @param message a human-readable description of why the product is invalid
     */
    public InvalidProductException(String message) {
        super(message);
    }

    /**
     * Creates the exception identifying the unavailable product by its ID.
     *
     * @param productId the ID of the product that does not exist or is not available
     */
    public InvalidProductException(Long productId) {
        super("Product with ID " + productId + " does not exist or is not available");
    }
}
