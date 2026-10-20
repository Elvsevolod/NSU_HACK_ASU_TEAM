package com.shoppingcart.auth.application.command.dto;

/**
 * Command DTO carrying the credentials required to authenticate an existing user.
 *
 * <p>Constructed by {@link com.shoppingcart.auth.framework.input.controller.AuthController}
 * from the incoming {@link com.shoppingcart.auth.framework.input.dto.LoginRequestDTO} and
 * passed to {@link com.shoppingcart.auth.application.command.port.input.LoginUserPort#execute(LoginCommand)}.</p>
 *
 * @param email    the user's registered e-mail address
 * @param password the plain-text password to verify against the stored BCrypt hash
 */
public record LoginCommand(String email, String password) {
}