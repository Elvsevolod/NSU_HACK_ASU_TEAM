package com.shoppingcart.product.application.query.port.input;

import com.shoppingcart.product.domain.entity.Product;
import com.shoppingcart.product.domain.vo.ProductId;

/**
 * Input port for retrieving a single product by its identifier.
 * 
 * This port defines the contract for querying a product from the system using
 * its unique identifier. It is part of the application layer and acts as an
 * interface between the presentation layer and the application logic.
 */
public interface GetProductPort {
    /**
     * Retrieves a product by its unique identifier.
     * 
     * @param id the unique product identifier
     * @return the Product entity with the specified identifier
     * @throws ProductNotFoundException if no product with the given ID exists
     */
    Product execute(ProductId id);
}
