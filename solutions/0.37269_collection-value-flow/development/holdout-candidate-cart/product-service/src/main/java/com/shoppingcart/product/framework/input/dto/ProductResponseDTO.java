package com.shoppingcart.product.framework.input.dto;

import java.math.BigDecimal;

/**
 * Data Transfer Object for product responses sent to clients.
 * 
 * This record encapsulates the product data returned in REST API responses.
 * It represents the external API contract and is mapped from domain Product
 * entities by ProductResponseMapper.
 * 
 * All price values are represented as BigDecimal to ensure precision and
 * avoid floating-point arithmetic issues with monetary values.
 * 
 * @param id the unique product identifier
 * @param title the product title
 * @param price the product price as BigDecimal with 2 decimal places
 * @param description the product description
 * @param category the product category name
 * @param image the product image URL
 */
public record ProductResponseDTO(
        Long id,
        String title,
        BigDecimal price,
        String description,
        String category,
        String image) {
}
