package com.shoppingcart.product.application.query.usecase;

import com.shoppingcart.product.application.query.port.output.ProductRepository;
import com.shoppingcart.product.domain.entity.Product;
import com.shoppingcart.product.domain.exceptions.ProductNotFoundException;
import com.shoppingcart.product.domain.vo.ProductId;

/**
 * Use case for retrieving a product by its identifier.
 * 
 * This use case encapsulates the business logic for fetching a single product.
 * It queries the repository and handles the case where the product is not found
 * by throwing a ProductNotFoundException.
 */
public class GetProductUseCase {

    private final ProductRepository productRepository;

    /**
     * Constructs a GetProductUseCase with a ProductRepository.
     * 
     * @param productRepository the repository for accessing product data
     */
    public GetProductUseCase(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    /**
     * Executes the use case to retrieve a product by its identifier.
     * 
     * @param id the unique product identifier
     * @return the Product with the specified identifier
     * @throws ProductNotFoundException if no product with the given ID exists
     */
    public Product execute(ProductId id) {
        return productRepository.findById(id)
                .orElseThrow(() -> new ProductNotFoundException(id.value()));
    }

    
}
