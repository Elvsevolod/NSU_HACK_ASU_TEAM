package com.shoppingcart.auth.domain.exception;

/**
 * Abstract base class for all domain-level exceptions in the auth-service.
 *
 * <p>Each concrete subclass supplies a fixed machine-readable {@code code} string
 * (e.g. {@code "INVALID_EMAIL"}, {@code "USER_NOT_FOUND"}) that the
 * {@link com.shoppingcart.auth.framework.exceptions.GlobalExceptionHandler} forwards in the
 * {@code errorCode} field of every error response, allowing API clients to
 * distinguish failure reasons programmatically.</p>
 */
public abstract class DomainException extends RuntimeException {
    private final String code;

    /**
     * @param message human-readable description of the failure
     * @param code    machine-readable error code included in the HTTP error response
     */
    public DomainException(String message, String code) {
        super(message);
        this.code = code;
    }

    /** @return the machine-readable error code for this exception */
    public String getCode() { return code; }
}
