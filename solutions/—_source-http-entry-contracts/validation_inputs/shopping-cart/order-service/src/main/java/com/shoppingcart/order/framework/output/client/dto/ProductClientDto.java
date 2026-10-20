package com.shoppingcart.order.framework.output.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Data Transfer Object representing the response from the external product service.
 *
 * <p>Maps the JSON fields returned by the product service API. The {@code image} field
 * uses {@link JsonProperty} to align with the API's field naming convention.
 * This record is internal to the framework layer and must not leak into the application
 * or domain layers.</p>
 *
 * @param id          the product's unique identifier
 * @param title       the product title as returned by the product service
 * @param price       the current price of the product
 * @param description a short description of the product
 * @param category    the category the product belongs to
 * @param image       the URL of the product image
 */
public record ProductClientDto(
    Long id,
    String title,
    Double price,
    String description,
    String category,
    @JsonProperty("image")
    String image
) {
}
