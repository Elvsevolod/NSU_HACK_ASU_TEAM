package com.shoppingcart.product.framework.input.controller;

import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.shoppingcart.product.application.query.port.input.GetProductPort;
import com.shoppingcart.product.application.query.port.input.ListProductsPort;
import com.shoppingcart.product.application.query.port.input.ListProductsByCategoryPort;
import com.shoppingcart.product.domain.vo.ProductId;
import com.shoppingcart.product.framework.input.dto.ProductResponseDTO;
import com.shoppingcart.product.framework.input.mapper.ProductResponseMapper;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;

/**
 * REST controller for product-related endpoints.
 * 
 * This controller handles HTTP requests from clients and exposes the product
 * query operations through REST endpoints. It acts as an adapter between the
 * external HTTP interface and the application layer's input ports.
 * 
 * The controller:
 * - Receives HTTP requests on /api/products endpoint
 * - Delegates business logic to input ports (GetProductPort, ListProductsPort, ListProductsByCategoryPort)
 * - Maps domain entities to response DTOs
 * - Returns properly formatted HTTP responses
 * 
 * All endpoints are documented with OpenAPI/Swagger annotations for API documentation.
 */
@Tag(name = "Products", description = "Product catalog")
@RestController
@RequestMapping("/api/products")
@RequiredArgsConstructor
public class ProductController {

    private final ListProductsPort listProducts;
    private final GetProductPort getProduct;
    private final ListProductsByCategoryPort listProductsByCategory;
    private final ProductResponseMapper mapper;

    /**
     * Retrieves all available products.
     * 
     * HTTP GET endpoint: /api/products
     * Returns a list of all products in the catalog.
     * 
     * @return a ResponseEntity containing a list of ProductResponseDTO
     * @response 200 OK - List of products successfully retrieved
     */
    @Operation(summary = "List all products")
    @ApiResponse(responseCode = "200", description = "List of products")
    @GetMapping
    public ResponseEntity<List<ProductResponseDTO>> getAll() {
        return ResponseEntity.ok(
                listProducts.execute().stream()
                        .map(mapper::toDTO)
                        .toList());
    }

    /**
     * Retrieves a single product by its ID.
     * 
     * HTTP GET endpoint: /api/products/{id}
     * Returns detailed information about a specific product.
     * 
     * @param id the product identifier from the URL path
     * @return a ResponseEntity containing the ProductResponseDTO
     * @response 200 OK - Product found and returned
     * @response 404 Not Found - Product with the specified ID does not exist
     */
    @Operation(summary = "Get product by ID")
    @ApiResponse(responseCode = "200", description = "Product found")
    @ApiResponse(responseCode = "404", description = "Product not found")
    @GetMapping("/{id}")
    public ResponseEntity<ProductResponseDTO> getById(@PathVariable Long id) {
        return ResponseEntity.ok(mapper.toDTO(getProduct.execute(new ProductId(id))));
    }

    /**
     * Retrieves all products in a specific category.
     * 
     * HTTP GET endpoint: /api/products/category/{category}
     * Returns a list of products filtered by the specified category name.
     * 
     * @param category the category name to filter by from the URL path
     * @return a ResponseEntity containing a list of ProductResponseDTO in the specified category
     * @response 200 OK - List of products in the category successfully retrieved
     */
    @Operation(summary = "List products by category")
    @ApiResponse(responseCode = "200", description = "List of products in the category")
    @GetMapping("/category/{category}")
    public ResponseEntity<List<ProductResponseDTO>> getByCategory(@PathVariable String category) {
        return ResponseEntity.ok(
                listProductsByCategory.execute(category).stream()
                        .map(mapper::toDTO)
                        .toList());
    }
}
