package com.shoppingcart.payment.domain.exceptions;

/**
 * Thrown when the order-service does not return a valid order for the given identifier.
 *
 * <p>Raised by the {@link com.shoppingcart.payment.framework.output.client.adapters.OrderClientAdapter}
 * when the order-service responds with a 404 or returns a null body, signalling that no
 * order exists for the requested ID.</p>
 */
public class OrderNotFoundException extends RuntimeException {

    /**
     * @param orderId the identifier for which no order was found in the order-service
     */
    public OrderNotFoundException(Long orderId) {
        super("Order not found with ID: " + orderId);
    }
}
