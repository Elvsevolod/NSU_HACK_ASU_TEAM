package com.shoppingcart.order.framework.exceptions;

import java.time.LocalDateTime;
import java.util.List;

import lombok.Getter;

/**
 * Standardized error response body returned by {@link GlobalExceptionHandler} for all error HTTP responses.
 *
 * <p>Provides a consistent structure across all error codes so clients can handle failures
 * uniformly. The {@code timestamp} is set automatically to the moment the instance is created.</p>
 */
@Getter
public class ErrorResponseDTO {

    /** The HTTP status code (e.g., 400, 404, 409, 500). */
    private final int status;

    /** Short human-readable HTTP status label (e.g., "Not Found", "Bad Request"). */
    private final String error;

    /** Application-level error code for programmatic handling (e.g., "ORDER_NOT_FOUND"). */
    private final String errorCode;

    /** Human-readable description of what went wrong. */
    private final String message;

    /** The moment the error response was generated, set at construction time. */
    private final LocalDateTime timestamp;

    /** The request URI that triggered the error. */
    private final String path;

    /** Optional list of field-level validation error messages; {@code null} when not applicable. */
    private final List<String> details;

    /**
     * Constructs an error response without field-level details.
     *
     * @param status    the HTTP status code
     * @param error     the short HTTP status label
     * @param errorCode the application-level error code
     * @param message   the human-readable error description
     * @param path      the request URI that triggered the error
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
     * Constructs an error response with field-level validation details.
     *
     * @param status    the HTTP status code
     * @param error     the short HTTP status label
     * @param errorCode the application-level error code
     * @param message   the human-readable error description
     * @param path      the request URI that triggered the error
     * @param details   a list of field-level validation messages
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
