package com.shoppingcart.auth.application.command.port.output;

/**
 * Output port for generating JWT authentication tokens.
 *
 * <p>Implemented by {@link com.shoppingcart.auth.framework.config.JwtService}, which signs
 * tokens with the configured HMAC-SHA256 secret and expiration. Abstracting token generation
 * here keeps use cases independent of the JWT library and signing configuration.</p>
 */
public interface TokenGeneratorPort {

    /**
     * Generates a signed JWT with the given e-mail as the subject claim.
     *
     * @param email the authenticated user's e-mail address, used as the JWT subject
     * @return a compact, URL-safe JWT string
     */
    String generateToken(String email);
}
