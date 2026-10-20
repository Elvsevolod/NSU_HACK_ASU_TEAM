package com.shoppingcart.product.framework.exceptions;

import java.time.LocalDateTime;
import java.util.List;

import lombok.Getter;

/**
 * Data Transfer Object for error responses.
 * 
 * This class encapsulates error information to be returned to clients when
 * an error occurs. It provides a standardized format containing HTTP status,
 * error type, error code, message, timestamp, request path, and optional
 * detailed error information.
 * 
 * All fields are immutable and populated through constructor parameters.
 */
@Getter
public class ErrorResponseDTO {

    private final int status;
    private final String error;
    private final String errorCode;
    private final String message;
    private final LocalDateTime timestamp;
    private final String path;
    private final List<String> details;

    /**
     * Constructs an ErrorResponseDTO with basic error information.
     * 
     * @param status the HTTP status code
     * @param error the HTTP error status name (e.g., "Bad Request", "Not Found")
     * @param errorCode a custom error code for programmatic handling
     * @param message a human-readable error message
     * @param path the request URI path where the error occurred
     */
    public ErrorResponseDTO(int status, String error, String errorCode, String message, String path) {
        this.status = status;
        this.error = error;
        this.errorCode = errorCode;
        this.message = message;
        this.timestamp = LocalDateTime.now();
        this.path = path;
        this.details = null;
    }

    /**
     * Constructs an ErrorResponseDTO with basic error information and detailed error list.
     * 
     * This constructor is used when the error response requires a list of detailed
     * error information, such as validation errors for individual fields.
     * 
     * @param status the HTTP status code
     * @param error the HTTP error status name (e.g., "Bad Request", "Not Found")
     * @param errorCode a custom error code for programmatic handling
     * @param message a human-readable error message
     * @param path the request URI path where the error occurred
     * @param details a list of detailed error messages or field validation errors
     */
    public ErrorResponseDTO(int status, String error, String errorCode, String message, String path,
            List<String> details) {
        this.status = status;
        this.error = error;
        this.errorCode = errorCode;
        this.message = message;
        this.timestamp = LocalDateTime.now();
        this.path = path;
        this.details = details;
    }
}
