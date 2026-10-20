package com.shoppingcart.auth.framework.input.dto;

/**
 * Response DTO carrying the JWT issued after a successful login or registration.
 *
 * @param token the signed JWT; must be included as {@code Authorization: Bearer <token>}
 *              on subsequent requests to protected endpoints
 */
public record AuthResponseDTO(String token) {}
