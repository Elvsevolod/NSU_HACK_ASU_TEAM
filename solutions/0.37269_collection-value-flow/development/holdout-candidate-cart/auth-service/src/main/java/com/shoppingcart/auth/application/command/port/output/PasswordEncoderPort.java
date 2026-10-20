package com.shoppingcart.auth.application.command.port.output;

/**
 * Output port that abstracts password hashing from the application layer.
 *
 * <p>Implemented by {@link com.shoppingcart.auth.framework.config.PasswordEncoderAdapter},
 * which delegates to Spring Security's {@code BCryptPasswordEncoder}. Keeping this port
 * in the application layer lets use cases remain independent of the hashing algorithm.</p>
 */
public interface PasswordEncoderPort {

    /**
     * Encodes a plain-text password using the configured hashing algorithm.
     *
     * @param rawPassword the plain-text password to encode
     * @return the BCrypt hash
     */
    String encode(String rawPassword);

    /**
     * Verifies that a plain-text password matches a previously encoded hash.
     *
     * @param rawPassword     the plain-text password supplied by the user
     * @param encodedPassword the BCrypt hash stored in the database
     * @return {@code true} if the passwords match, {@code false} otherwise
     */
    boolean matches(String rawPassword, String encodedPassword);
}
