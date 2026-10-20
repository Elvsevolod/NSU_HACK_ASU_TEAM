package com.shoppingcart.product.application.query.port.output;

import java.util.List;
import java.util.Optional;

import com.shoppingcart.product.domain.entity.Product;
import com.shoppingcart.product.domain.vo.ProductId;

/**
 * Output port for product persistence operations.
 * 
 * This port defines the contract for interacting with the product storage system.
 * It is part of the application layer and provides data access abstraction,
 * allowing the business logic to remain independent of the persistence mechanism.
 * Implementations of this port are adapters responsible for communicating with
 * the actual data store (database, cache, etc.).
 */
public interface ProductRepository {
    /**
     * Retrieves all products from the repository.
     * 
     * @return a list containing all Product entities in the repository,
     *         or an empty list if no products exist
     */
    List<Product> findAll();

    /**
     * Retrieves a product by its unique identifier.
     * 
     * @param id the unique product identifier to search for
     * @return an Optional containing the Product if found, or an empty Optional
     *         if no product with the given ID exists
     */
    Optional<Product> findById(ProductId id);

    /**
     * Retrieves all products belonging to a specific category.
     * 
     * @param category the category name to filter products by
     * @return a list of Product entities matching the specified category,
     *         or an empty list if no products are found in that category
     */
    List<Product> findByCategory(String category);
}