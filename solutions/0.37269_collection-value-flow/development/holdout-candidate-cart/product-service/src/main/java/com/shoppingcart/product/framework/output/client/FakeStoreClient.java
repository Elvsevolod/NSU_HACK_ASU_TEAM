package com.shoppingcart.product.framework.output.client;

import java.util.List;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

import com.shoppingcart.product.framework.output.client.dto.FakeStoreProductResponse;

/**
 * Feign client for the FakeStore external API.
 * 
 * This interface defines HTTP endpoints for communicating with the FakeStore API.
 * It uses Spring Cloud Feign to automatically generate the HTTP client implementation.
 * The base URL is configured via the application properties (fakestore.base-url).
 * 
 * The client provides methods for retrieving product information from the external
 * FakeStore API, which serves as the data source for the product repository.
 */
@FeignClient(name = "fakestore-client", url = "${fakestore.base-url}")
public interface FakeStoreClient {

    /**
     * Retrieves all products from the FakeStore API.
     * 
     * Makes a GET request to /products endpoint.
     * 
     * @return a list of FakeStoreProductResponse containing all available products
     */
    @GetMapping("/products")
    List<FakeStoreProductResponse> getAllProducts();

    @GetMapping("/products/{id}")
    FakeStoreProductResponse getProductById(@PathVariable("id") Long id);

    @GetMapping("/products/category/{category}")
    List<FakeStoreProductResponse> getProductsByCategory(@PathVariable("category") String category);
}
