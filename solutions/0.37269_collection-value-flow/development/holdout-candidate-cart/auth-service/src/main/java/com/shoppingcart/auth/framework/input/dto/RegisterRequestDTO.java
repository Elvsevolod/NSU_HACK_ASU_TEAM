package com.shoppingcart.auth.framework.input.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Request DTO for the {@code POST /api/auth/register} endpoint.
 *
 * <p>Bean Validation constraints mirror the domain invariants enforced by
 * {@link com.shoppingcart.auth.domain.vo.Email} and
 * {@link com.shoppingcart.auth.domain.vo.Password}, providing early feedback at the HTTP
 * boundary before the request reaches the application layer.</p>
 *
 * @param email    the desired e-mail address; must be non-blank and well-formed
 * @param password the desired password; must be non-blank and at least 8 characters
 */
public record RegisterRequestDTO(

        @NotBlank(message = "Email is required")
        @Email(message = "Email format is invalid")
        String email,

        @NotBlank(message = "Password is required")
        @Size(min = 8, message = "Password must be at least 8 characters")
        String password
) {}
