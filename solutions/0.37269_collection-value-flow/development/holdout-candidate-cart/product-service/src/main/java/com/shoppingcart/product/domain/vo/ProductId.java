package com.shoppingcart.product.domain.vo;

import com.shoppingcart.product.domain.exceptions.ProductValidationException;

/**
 * Value object representing a unique product identifier.
 * 
 * This record encapsulates a Long value as the product's unique identifier and
 * ensures data integrity through validation in the compact constructor. The product
 * ID must be a positive number.
 * 
 * @param value the unique product identifier (must be a positive number > 0)
 */
public record ProductId(Long value) {

    public ProductId {
        if (value == null || value <= 0)
            throw new ProductValidationException("id", "must be a positive number");
    }
}
