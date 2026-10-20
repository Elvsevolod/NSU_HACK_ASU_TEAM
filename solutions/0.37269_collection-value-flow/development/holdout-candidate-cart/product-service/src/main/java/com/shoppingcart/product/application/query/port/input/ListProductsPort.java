package com.shoppingcart.product.application.query.port.input;


import java.util.List;

import com.shoppingcart.product.domain.entity.Product;

/**
 * Input port for retrieving all products.
 * 
 * This port defines the contract for querying all available products from
 * the system. It is part of the application layer and acts as an interface
 * between the presentation layer and the application logic.
 */
public interface ListProductsPort {
    /**
     * Retrieves all available products.
     * 
     * @return a list of all Product entities in the system,
     *         or an empty list if no products exist
     */
    List<Product> execute();
}
