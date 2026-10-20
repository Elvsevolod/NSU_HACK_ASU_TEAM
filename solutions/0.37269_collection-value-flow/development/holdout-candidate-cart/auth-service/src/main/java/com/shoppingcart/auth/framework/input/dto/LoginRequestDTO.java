package com.shoppingcart.auth.framework.input.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * Request DTO for the {@code POST /api/auth/login} endpoint.
 *
 * <p>Bean Validation is applied at the controller layer before the command is forwarded
 * to the application layer. Domain-level validations (e-mail format, password length) are
 * re-enforced inside the domain value objects regardless.</p>
 *
 * @param email    the registered e-mail address; must not be blank
 * @param password the plain-text password to verify; must not be blank
 */
public record LoginRequestDTO(

        @NotBlank(message = "Email is required")
        String email,

        @NotBlank(message = "Password is required")
        String password
) {}
