package com.shoppingcart.product.framework.output.mapper;

import org.springframework.stereotype.Component;

import com.shoppingcart.product.domain.entity.Product;
import com.shoppingcart.product.framework.output.client.dto.FakeStoreProductResponse;

/**
 * Mapper for converting FakeStore API responses to domain entities.
 * 
 * This component is responsible for transforming FakeStoreProductResponse DTOs
 * (from the external API) into domain Product entities. It acts as a translator
 * between the external API representation and the domain model, ensuring the
 * domain remains independent of external dependencies.
 * 
 * This mapper implements the mapping logic for the adapter pattern in hexagonal
 * architecture, decoupling the domain from framework-specific concerns.
 */
@Component
public class FakeStoreProductMapper {

    /**
     * Converts a FakeStoreProductResponse to a domain Product entity.
     * 
     * This method transforms the external API response into a domain Product
     * by calling the Product's reconstitute factory method. The reconstitute
     * method ensures that all domain validation and normalization rules are applied.
     * 
     * @param response the FakeStoreProductResponse from the external API
     * @return a domain Product entity with the mapped data
     */
    public Product toDomain(FakeStoreProductResponse response) {
        return Product.reconstitute(
                response.id(),
                response.title(),
                response.price(),
                response.description(),
                response.category(),
                response.image());
    }
}
