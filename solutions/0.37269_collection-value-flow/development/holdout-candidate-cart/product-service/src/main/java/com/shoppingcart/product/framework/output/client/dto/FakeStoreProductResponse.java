package com.shoppingcart.product.framework.output.client.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/**
 * Data Transfer Object for FakeStore API product responses.
 * 
 * This record encapsulates the product data returned by the FakeStore API.
 * It uses Jackson annotations to ignore unknown fields from the API response,
 * ensuring compatibility even if the API response structure changes.
 * 
 * The response is mapped to the domain Product entity by FakeStoreProductMapper.
 * 
 * @param id the unique product identifier
 * @param title the product title
 * @param price the product price
 * @param description the product description
 * @param category the product category
 * @param image the product image URL
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record FakeStoreProductResponse(
        Long id,
        String title,
        Double price,
        String description,
        String category,
        String image) {
}
