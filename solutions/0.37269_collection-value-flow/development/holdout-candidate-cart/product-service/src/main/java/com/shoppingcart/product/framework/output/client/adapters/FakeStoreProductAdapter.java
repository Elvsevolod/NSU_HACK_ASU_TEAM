package com.shoppingcart.product.framework.output.client.adapters;

import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Component;

import com.shoppingcart.product.application.query.port.output.ProductRepository;
import com.shoppingcart.product.domain.entity.Product;
import com.shoppingcart.product.domain.vo.ProductId;
import com.shoppingcart.product.framework.output.client.FakeStoreClient;
import com.shoppingcart.product.framework.output.mapper.FakeStoreProductMapper;

import lombok.RequiredArgsConstructor;

/**
 * Adapter that implements the ProductRepository port using FakeStore API.
 * 
 * This class acts as an adapter between the application layer (which expects
 * a ProductRepository) and the FakeStore external API. It translates API responses
 * into domain entities, following the Adapter pattern from hexagonal architecture.
 * 
 * The adapter is responsible for:
 * - Making HTTP calls to the FakeStore API via FakeStoreClient
 * - Mapping FakeStoreProductResponse DTOs to domain Product entities
 * - Handling optional results and stream transformations
 */
@Component
@RequiredArgsConstructor
public class FakeStoreProductAdapter implements ProductRepository {

    private final FakeStoreClient fakeStoreClient;
    private final FakeStoreProductMapper mapper;

    /**
     * Retrieves all products from the FakeStore API.
     * 
     * Calls the FakeStore API to get all products and maps each response
     * to a domain Product entity.
     * 
     * @return a list of Product domain entities
     */
    @Override
    public List<Product> findAll() {
        return fakeStoreClient.getAllProducts().stream()
                .map(mapper::toDomain)
                .toList();
    }

    /**
     * Retrieves a product by its ID from the FakeStore API.
     * 
     * Calls the FakeStore API to get a single product and maps the response
     * to a domain Product entity. Returns an empty Optional if not found.
     * 
     * @param id the product identifier
     * @return an Optional containing the Product if found, or empty if not found
     */
    @Override
    public Optional<Product> findById(ProductId id) {
        return Optional.ofNullable(fakeStoreClient.getProductById(id.value()))
                .map(mapper::toDomain);
    }

    /**
     * Retrieves all products in a specific category from the FakeStore API.
     * 
     * Calls the FakeStore API to get products filtered by category and maps
     * each response to a domain Product entity.
     * 
     * @param category the category name to filter by
     * @return a list of Product domain entities in the specified category
     */
    @Override
    public List<Product> findByCategory(String category) {
        return fakeStoreClient.getProductsByCategory(category).stream()
                .map(mapper::toDomain)
                .toList();
    }
}
