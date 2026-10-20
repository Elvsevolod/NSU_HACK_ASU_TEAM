package com.shoppingcart.auth.domain.exception;

/**
 * Thrown when no user matching the supplied e-mail address can be found in the persistence layer.
 *
 * <p>Raised by {@link com.shoppingcart.auth.application.command.usecase.LoginUserUseCase} and
 * {@link com.shoppingcart.auth.application.query.usecase.FindUserUseCase}.
 * Mapped to HTTP 404 Not Found by
 * {@link com.shoppingcart.auth.framework.exceptions.GlobalExceptionHandler}
 * with error code {@code USER_NOT_FOUND}.</p>
 */
public class UserNotFoundException extends DomainException {

    /**
     * @param email the e-mail address for which no user was found
     */
    public UserNotFoundException(String email) {
        super("User not found: " + email, "USER_NOT_FOUND");
    }
}