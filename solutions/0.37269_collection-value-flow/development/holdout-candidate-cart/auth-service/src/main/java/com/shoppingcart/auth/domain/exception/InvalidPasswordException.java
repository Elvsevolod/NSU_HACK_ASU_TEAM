package com.shoppingcart.auth.domain.exception;

/**
 * Thrown when a plain-text password fails the minimum-length rule enforced by
 * {@link com.shoppingcart.auth.domain.vo.Password#ofPlainText(String)}, or when the
 * supplied credentials do not match during login.
 *
 * <p>Mapped to HTTP 400 Bad Request by
 * {@link com.shoppingcart.auth.framework.exceptions.GlobalExceptionHandler}
 * with error code {@code INVALID_PASSWORD}.</p>
 */
public class InvalidPasswordException extends DomainException {

    /**
     * @param message description of the validation failure or credential mismatch
     */
    public InvalidPasswordException(String message) {
        super(message, "INVALID_PASSWORD");
    }
}