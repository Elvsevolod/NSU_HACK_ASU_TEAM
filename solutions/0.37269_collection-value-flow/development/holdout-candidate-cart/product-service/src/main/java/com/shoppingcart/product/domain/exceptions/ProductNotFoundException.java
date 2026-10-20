package com.shoppingcart.product.domain.exceptions;

/**
 * Exception thrown when a product cannot be found in the system.
 * 
 * This is a runtime exception that is thrown when attempting to retrieve a product
 * that does not exist in the database or repository. It extends RuntimeException
 * to indicate an unrecoverable error condition.
 */
public class ProductNotFoundException extends RuntimeException {

    /**
     * Constructs a ProductNotFoundException with a custom message.
     * 
     * @param message the detail message explaining why the product was not found
     */
    public ProductNotFoundException(String message) {
        super(message);
    }

    /**
     * Constructs a ProductNotFoundException with a product ID.
     * 
     * This constructor automatically formats a message indicating that a product
     * with the specified ID was not found.
     * 
     * @param id the product ID that was not found
     */
    public ProductNotFoundException(Long id) {
        super("Product with ID " + id + " not found");
    }
}
