package com.shoppingcart.auth.domain.exception;

/**
 * Thrown when a string cannot be resolved to a known {@link com.shoppingcart.auth.domain.vo.Role}
 * constant by {@link com.shoppingcart.auth.domain.vo.Role#from(String)}.
 *
 * <p>Mapped to HTTP 400 Bad Request by
 * {@link com.shoppingcart.auth.framework.exceptions.GlobalExceptionHandler}
 * with error code {@code INVALID_ROLE}.</p>
 */
public class InvalidRoleException extends DomainException {

    /**
     * @param message description of the unrecognised role value
     */
    public InvalidRoleException(String message) {
        super(message, "INVALID_ROLE");
    }
}
