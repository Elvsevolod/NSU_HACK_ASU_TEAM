package com.shoppingcart.auth.application.command.port.input;

import com.shoppingcart.auth.application.command.dto.LoginCommand;

/**
 * Input port for the login use case.
 *
 * <p>Implemented by {@link com.shoppingcart.auth.application.command.service.AuthCommandService}
 * and called by {@link com.shoppingcart.auth.framework.input.controller.AuthController}.</p>
 */
public interface LoginUserPort {

    /**
     * Authenticates a user and issues a JWT.
     *
     * @param command the login credentials
     * @return a signed JWT token for the authenticated user
     * @throws com.shoppingcart.auth.domain.exception.UserNotFoundException    if no user exists with the supplied e-mail
     * @throws com.shoppingcart.auth.domain.exception.InvalidPasswordException if the password does not match the stored hash
     */
    String execute(LoginCommand command);
}
