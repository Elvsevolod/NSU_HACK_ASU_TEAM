package com.shoppingcart.auth.domain.exception;

/**
 * Thrown during registration when a user with the supplied e-mail address already exists.
 *
 * <p>Raised by {@link com.shoppingcart.auth.application.command.usecase.RegisterUserUseCase}
 * after a duplicate e-mail check against the persistence layer.
 * Mapped to HTTP 409 Conflict by
 * {@link com.shoppingcart.auth.framework.exceptions.GlobalExceptionHandler}
 * with error code {@code USER_ALREADY_EXISTS}.</p>
 */
public class UserAlreadyExistsException extends DomainException {

    /**
     * @param email the e-mail address that is already registered
     */
    public UserAlreadyExistsException(String email) {
        super("User already exists with email: " + email, "USER_ALREADY_EXISTS");
    }
}
