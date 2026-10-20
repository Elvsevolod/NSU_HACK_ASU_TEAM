package com.shoppingcart.product.domain.vo;

import com.shoppingcart.product.domain.exceptions.ProductValidationException;

/**
 * Value object representing a product category.
 * 
 * This record encapsulates a category name and ensures data integrity through
 * validation in the compact constructor. The category name is normalized by
 * trimming whitespace and converting to lowercase.
 * 
 * @param name the category name (must not be null or blank)
 */
public record Category(String name) {

    public Category {
        if (name == null || name.isBlank())
            throw new ProductValidationException("category", "cannot be blank");
        name = name.trim().toLowerCase();
    }
}
