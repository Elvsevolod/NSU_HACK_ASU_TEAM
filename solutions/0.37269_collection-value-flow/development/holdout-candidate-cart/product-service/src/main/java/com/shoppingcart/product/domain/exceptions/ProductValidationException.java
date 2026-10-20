package com.shoppingcart.product.domain.exceptions;

/**
 * Exception thrown when product data validation fails.
 * 
 * This is a runtime exception that is thrown when a product or its attributes
 * fail validation constraints. It extends RuntimeException to indicate an
 * unrecoverable error condition that prevents object creation or modification.
 */
public class ProductValidationException extends RuntimeException {

    /**
     * Constructs a ProductValidationException with a custom message.
     * 
     * @param message the detail message explaining the validation failure
     */
    public ProductValidationException(String message) {
        super(message);
    }

    /**
     * Constructs a ProductValidationException with a field name and validation error message.
     * 
     * This constructor automatically formats a message indicating which field failed
     * validation and why.
     * 
     * @param field the name of the field that failed validation
     * @param message the validation error message describing the failure reason
     */
    public ProductValidationException(String field, String message) {
        super("Validation failed for '" + field + "': " + message);
    }
}
