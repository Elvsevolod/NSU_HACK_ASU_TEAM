package com.shoppingcart.order.application.command.port.output;

/**
 * Output port for querying product prices from an external product catalog.
 *
 * <p>The application layer depends on this interface to validate that the unit price supplied
 * by a client matches the authoritative price in the product service. The framework layer
 * provides the implementation (e.g., an HTTP client adapter calling the product service).</p>
 */
public interface ProductValidationPort {

    /**
     * Retrieves the current price of a product from the product catalog.
     *
     * @param productId the identifier of the product to look up
     * @return the product's current price
     * @throws com.shoppingcart.order.domain.exceptions.InvalidProductException if the product
     *         does not exist or is not available in the catalog
     */
    Double getProductPrice(Long productId);
}
