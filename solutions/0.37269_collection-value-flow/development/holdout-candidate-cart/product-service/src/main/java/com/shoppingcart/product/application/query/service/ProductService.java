package com.shoppingcart.product.application.query.service;



import com.shoppingcart.product.application.query.port.input.GetProductPort;
import com.shoppingcart.product.application.query.port.input.ListProductsByCategoryPort;
import com.shoppingcart.product.application.query.port.input.ListProductsPort;
import com.shoppingcart.product.application.query.port.output.ProductRepository;
import com.shoppingcart.product.application.query.usecase.GetProductUseCase;
import com.shoppingcart.product.application.query.usecase.ListProductsByCategoryUseCase;
import com.shoppingcart.product.application.query.usecase.ListProductsUseCase;
import com.shoppingcart.product.domain.entity.Product;
import com.shoppingcart.product.domain.vo.ProductId;

import java.util.List;

/**
 * Service class that orchestrates query operations for products.
 * 
 * This service implements the input ports and acts as a facade that coordinates
 * the execution of use cases. It delegates the actual business logic to specialized
 * use case classes, maintaining separation of concerns and following the Single
 * Responsibility Principle.
 * 
 * The service implements the following ports:
 * - ListProductsPort: Retrieve all products
 * - GetProductPort: Retrieve a product by ID
 * - ListProductsByCategoryPort: Retrieve products by category
 */
public class ProductService implements
        ListProductsPort,
        GetProductPort,
        ListProductsByCategoryPort {

    private final GetProductUseCase getProductUseCase;
    private final ListProductsUseCase listProductsUseCase;
    private final ListProductsByCategoryUseCase listProductsByCategory;

    /**
     * Constructs a ProductService with a ProductRepository.
     * 
     * This constructor initializes all use case instances with the provided
     * repository, ensuring they have access to the data they need.
     * 
     * @param productRepository the repository for accessing product data
     */
    public ProductService(ProductRepository productRepository) {
        this.getProductUseCase = new GetProductUseCase(productRepository);
        this.listProductsUseCase = new ListProductsUseCase(productRepository);
        this.listProductsByCategory = new ListProductsByCategoryUseCase(productRepository);
    }

    /**
     * Retrieves all products in a specific category.
     * 
     * Implements ListProductsByCategoryPort. Delegates to ListProductsByCategoryUseCase.
     * 
     * @param category the category name to filter by
     * @return a list of products in the specified category
     */
    @Override
    public List<Product> execute(String category) {
       return this.listProductsByCategory.execute(category);
    }

    /**
     * Retrieves a product by its unique identifier.
     * 
     * Implements GetProductPort. Delegates to GetProductUseCase.
     * 
     * @param id the product identifier
     * @return the Product with the specified ID
     * @throws ProductNotFoundException if the product is not found
     */
    @Override
    public Product execute(ProductId id) {
       return this.getProductUseCase.execute(id);
    }

    /**
     * Retrieves all available products.
     * 
     * Implements ListProductsPort. Delegates to ListProductsUseCase.
     * 
     * @return a list of all products in the system
     */
    @Override
    public List<Product> execute() {
       return this.listProductsUseCase.execute();
    }


}
