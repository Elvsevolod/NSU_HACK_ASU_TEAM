package com.shoppingcart.product.framework.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.shoppingcart.product.application.query.port.input.GetProductPort;
import com.shoppingcart.product.application.query.port.input.ListProductsPort;
import com.shoppingcart.product.application.query.port.input.ListProductsByCategoryPort;
import com.shoppingcart.product.application.query.port.output.ProductRepository;
import com.shoppingcart.product.application.query.service.ProductService;

/**
 * Spring configuration class for application-level beans.
 * 
 * This configuration class is responsible for defining and wiring the application's
 * beans. It configures the input ports (GetProductPort, ListProductsPort,
 * ListProductsByCategoryPort) by creating instances of ProductService, which
 * implements all these ports. This ensures proper dependency injection and
 * decoupling between layers.
 * 
 * The configuration uses Spring's @Configuration and @Bean annotations to
 * manage bean creation and lifecycle. Dependencies are injected directly into
 * bean factory methods, eliminating the need for instance fields.
 */
@Configuration
public class ApplicationConfig {

    /**
     * Creates and registers a bean for the ListProductsPort.
     * 
     * This bean provides the interface for retrieving all products.
     * A ProductService instance is instantiated and registered as a Spring bean,
     * making it available for dependency injection throughout the application.
     * 
     * @param productRepository the repository for accessing product data, injected by Spring
     * @return a ListProductsPort implementation (ProductService instance)
     */
    @Bean
    public ListProductsPort listProducts(ProductRepository productRepository) {
        return new ProductService(productRepository);
    }

    /**
     * Creates and registers a bean for the GetProductPort.
     * 
     * This bean provides the interface for retrieving a single product by ID.
     * A ProductService instance is instantiated and registered as a Spring bean,
     * making it available for dependency injection throughout the application.
     * 
     * @param productRepository the repository for accessing product data, injected by Spring
     * @return a GetProductPort implementation (ProductService instance)
     */
    @Bean
    public GetProductPort getProduct(ProductRepository productRepository) {
        return new ProductService(productRepository);
    }

    /**
     * Creates and registers a bean for the ListProductsByCategoryPort.
     * 
     * This bean provides the interface for retrieving products filtered by category.
     * A ProductService instance is instantiated and registered as a Spring bean,
     * making it available for dependency injection throughout the application.
     * 
     * @param productRepository the repository for accessing product data, injected by Spring
     * @return a ListProductsByCategoryPort implementation (ProductService instance)
     */
    @Bean
    public ListProductsByCategoryPort listProductsByCategory(ProductRepository productRepository) {
        return new ProductService(productRepository);
    }
}
