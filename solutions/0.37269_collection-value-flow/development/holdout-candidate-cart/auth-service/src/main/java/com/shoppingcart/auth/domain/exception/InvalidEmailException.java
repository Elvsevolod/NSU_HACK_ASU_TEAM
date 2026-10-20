package com.shoppingcart.auth.domain.exception;

/**
 * Thrown when an e-mail address fails the format validation enforced by
 * {@link com.shoppingcart.auth.domain.vo.Email}.
 *
 * <p>Mapped to HTTP 400 Bad Request by
 * {@link com.shoppingcart.auth.framework.exceptions.GlobalExceptionHandler}
 * with error code {@code INVALID_EMAIL}.</p>
 */
public class InvalidEmailException extends DomainException {

    /**
     * @param message description of the invalid e-mail value
     */
    public InvalidEmailException(String message) {
        super(message, "INVALID_EMAIL");
    }
}