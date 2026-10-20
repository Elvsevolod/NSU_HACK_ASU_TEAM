package com.shoppingcart.auth.framework.exceptions;

import java.time.LocalDateTime;
import java.util.List;

import lombok.Getter;

/**
 * Standardised error response body returned by {@link GlobalExceptionHandler} for all error cases.
 *
 * <p>Fields:</p>
 * <ul>
 *   <li>{@code status} — the HTTP status code (e.g. 400, 404, 409, 500).</li>
 *   <li>{@code error} — the HTTP reason phrase (e.g. "Bad Request", "Not Found").</li>
 *   <li>{@code errorCode} — a machine-readable code from the domain exception (e.g. "USER_NOT_FOUND").</li>
 *   <li>{@code message} — a human-readable description of the failure.</li>
 *   <li>{@code timestamp} — the UTC instant at which the error was generated.</li>
 *   <li>{@code path} — the request URI that triggered the error.</li>
 *   <li>{@code details} — optional list of per-field validation messages; {@code null} for single-cause errors.</li>
 * </ul>
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
     * Constructs an error response without per-field detail messages.
     *
     * @param status    the HTTP status code
     * @param error     the HTTP reason phrase
     * @param errorCode the machine-readable domain error code
     * @param message   a human-readable description of the failure
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
     * Constructs an error response with per-field validation detail messages.
     *
     * @param status    the HTTP status code
     * @param error     the HTTP reason phrase
     * @param errorCode the machine-readable domain error code
     * @param message   a human-readable summary of the failure
     * @param path      the request URI that triggered the error
     * @param details   list of field-level validation messages (e.g. {@code "email: must not be blank"})
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
