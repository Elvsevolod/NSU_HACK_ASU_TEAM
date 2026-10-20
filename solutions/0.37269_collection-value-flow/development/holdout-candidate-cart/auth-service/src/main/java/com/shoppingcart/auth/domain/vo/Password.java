package com.shoppingcart.auth.domain.vo;

import com.shoppingcart.auth.domain.exception.InvalidPasswordException;

/**
 * Value object representing a user password, either as plain text or a BCrypt hash.
 *
 * <p>Two static factory methods enforce the two distinct creation paths:</p>
 * <ul>
 *   <li>{@link #ofPlainText(String)} — used during registration and login; validates the 8-character minimum.</li>
 *   <li>{@link #ofHash(String)} — used when reconstituting a {@link com.shoppingcart.auth.domain.entity.User}
 *       from the database; skips length validation because the hash was already validated at write time.</li>
 * </ul>
 *
 * <p>The record's canonical constructor is intentionally left unrestricted so that both factories
 * can delegate to it without duplicating guard logic.</p>
 */
public record Password(String value) {

    /**
     * Creates a {@code Password} from a plain-text string and enforces the minimum length.
     *
     * @param raw the plain-text password supplied by the user
     * @return a new {@code Password} wrapping the raw value
     * @throws InvalidPasswordException if {@code raw} is {@code null} or shorter than 8 characters
     */
    public static Password ofPlainText(String raw) {
        if (raw == null || raw.length() < 8)
            throw new InvalidPasswordException("Minimum 8 characters required");
        return new Password(raw);
    }

    /**
     * Wraps an existing BCrypt hash without length validation.
     *
     * @param hash the BCrypt hash loaded from the database
     * @return a new {@code Password} wrapping the hash
     */
    public static Password ofHash(String hash) {
        return new Password(hash);
    }
}