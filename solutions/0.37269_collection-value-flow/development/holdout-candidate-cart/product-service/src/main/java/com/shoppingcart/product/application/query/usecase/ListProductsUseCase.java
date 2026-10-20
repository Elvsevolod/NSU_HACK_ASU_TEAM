package com.shoppingcart.product.application.query.usecase;

import java.util.List;

import com.shoppingcart.product.application.query.port.output.ProductRepository;
import com.shoppingcart.product.domain.entity.Product;

/**
 * Use case for retrieving all available products.
 * 
 * This use case encapsulates the business logic for fetching all products from
 * the system. It delegates to the repository to retrieve the complete list.
 */
public class ListProductsUseCase {

    private final ProductRepository productRepository;

    /**
     * Constructs a ListProductsUseCase with a ProductRepository.
     * 
     * @param productRepository the repository for accessing product data
     */
    public ListProductsUseCase(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    /**
     * Executes the use case to retrieve all products.
     * 
     * @return a list of all Product entities in the system,
     *         or an empty list if no products exist
     */
    public List<Product> execute(){
        return productRepository.findAll();
    }
}
