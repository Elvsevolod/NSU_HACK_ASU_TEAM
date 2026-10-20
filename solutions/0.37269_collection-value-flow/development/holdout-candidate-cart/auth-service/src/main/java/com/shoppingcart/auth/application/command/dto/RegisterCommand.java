package com.shoppingcart.auth.application.command.dto;

/**
 * Command DTO carrying the credentials required to register a new user.
 *
 * <p>Constructed by {@link com.shoppingcart.auth.framework.input.controller.AuthController}
 * from the incoming {@link com.shoppingcart.auth.framework.input.dto.RegisterRequestDTO} and
 * passed to {@link com.shoppingcart.auth.application.command.port.input.RegisterUserPort#execute(RegisterCommand)}.</p>
 *
 * @param email    the desired e-mail address for the new account
 * @param password the plain-text password; domain validation enforces a minimum of 8 characters
 */
public record RegisterCommand(String email, String password) {
}
