package com.shoppingcart.product.framework.input.mapper;

import org.springframework.stereotype.Component;

import com.shoppingcart.product.domain.entity.Product;
import com.shoppingcart.product.framework.input.dto.ProductResponseDTO;

/**
 * Mapper for converting domain Product entities to response DTOs.
 * 
 * This component is responsible for transforming domain Product entities
 * into ProductResponseDTO objects suitable for REST API responses.
 * It acts as a translator between the domain model and the external API contract,
 * ensuring the domain remains independent of API-specific concerns.
 * 
 * This mapper implements the mapping logic for the adapter pattern in hexagonal
 * architecture, allowing the domain to be decoupled from framework-specific
 * presentation concerns.
 */
@Component
public class ProductResponseMapper {

    /**
     * Converts a domain Product entity to a ProductResponseDTO.
     * 
     * This method transforms the domain Product into a response DTO by extracting
     * the necessary values from value objects and domain entities.
     * The price is extracted as BigDecimal from the Money value object,
     * category name from the Category value object, and image URL from ProductImage.
     * 
     * @param product the domain Product entity to convert
     * @return a ProductResponseDTO with the mapped data
     */
    public ProductResponseDTO toDTO(Product product) {
        return new ProductResponseDTO(
                product.getId().value(),
                product.getTitle(),
                product.getPrice().amount(),
                product.getDescription(),
                product.getCategory().name(),
                product.getImage().url());
    }
}
