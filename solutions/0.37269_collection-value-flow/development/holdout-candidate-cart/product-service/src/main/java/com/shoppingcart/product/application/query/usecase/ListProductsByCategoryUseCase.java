package com.shoppingcart.product.application.query.usecase;

import java.util.List;

import com.shoppingcart.product.application.query.port.output.ProductRepository;
import com.shoppingcart.product.domain.entity.Product;

/**
 * Use case for retrieving products filtered by category.
 * 
 * This use case encapsulates the business logic for fetching products that
 * belong to a specific category. It delegates to the repository to filter
 * and retrieve matching products.
 */
public class ListProductsByCategoryUseCase {
    
      private final ProductRepository productRepository;

    /**
     * Constructs a ListProductsByCategoryUseCase with a ProductRepository.
     * 
     * @param productRepository the repository for accessing product data
     */
    public ListProductsByCategoryUseCase(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    /**
     * Executes the use case to retrieve products by category.
     * 
     * @param category the category name to filter products by
     * @return a list of Product entities matching the specified category,
     *         or an empty list if no products are found in that category
     */
    public List<Product> execute(String category){
        return productRepository.findByCategory(category);
    }
}
