package com.shoppingcart.product.domain.vo;

import com.shoppingcart.product.domain.exceptions.ProductValidationException;

/**
 * Value object representing a product image.
 * 
 * This record encapsulates a URL string pointing to a product image and ensures
 * data integrity through validation in the compact constructor. The URL must be
 * non-blank and start with http:// or https:// to ensure valid web accessibility.
 * 
 * @param url the URL of the product image (must not be blank and must start with http:// or https://)
 */
public record ProductImage(String url) {

    public ProductImage {
        if (url == null || url.isBlank())
            throw new ProductValidationException("image", "URL cannot be blank");
        if (!url.startsWith("http://") && !url.startsWith("https://"))
            throw new ProductValidationException("image", "URL must start with http:// or https://");
    }
}
