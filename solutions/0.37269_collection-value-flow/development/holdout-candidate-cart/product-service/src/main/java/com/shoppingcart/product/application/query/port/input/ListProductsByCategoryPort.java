package com.shoppingcart.product.application.query.port.input;

import java.util.List;

import com.shoppingcart.product.domain.entity.Product;

/**
 * Input port for retrieving all products in a specific category.
 * 
 * This port defines the contract for querying products filtered by category from
 * the system. It is part of the application layer and acts as an interface between
 * the presentation layer and the application logic.
 */
public interface ListProductsByCategoryPort {
    /**
     * Retrieves all products belonging to a specific category.
     * 
     * @param category the category name to filter products by
     * @return a list of Product entities matching the specified category,
     *         or an empty list if no products are found
     */
    List<Product> execute(String category);
}
