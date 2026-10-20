package com.shoppingcart.auth.application.command.port.input;

import com.shoppingcart.auth.application.command.dto.RegisterCommand;

/**
 * Input port for the user registration use case.
 *
 * <p>Implemented by {@link com.shoppingcart.auth.application.command.service.AuthCommandService}
 * and called by {@link com.shoppingcart.auth.framework.input.controller.AuthController}.</p>
 */
public interface RegisterUserPort {

    /**
     * Registers a new user and issues a JWT for immediate login.
     *
     * @param command the registration credentials
     * @return a signed JWT token for the newly registered user
     * @throws com.shoppingcart.auth.domain.exception.UserAlreadyExistsException if the e-mail is already registered
     * @throws com.shoppingcart.auth.domain.exception.InvalidEmailException       if the e-mail format is invalid
     * @throws com.shoppingcart.auth.domain.exception.InvalidPasswordException    if the password is shorter than 8 characters
     */
    String execute(RegisterCommand command);
}
