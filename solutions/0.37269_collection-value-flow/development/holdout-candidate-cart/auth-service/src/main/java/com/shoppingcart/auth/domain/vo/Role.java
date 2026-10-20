package com.shoppingcart.auth.domain.vo;

import com.shoppingcart.auth.domain.exception.InvalidRoleException;

/**
 * Enumeration of the roles that can be assigned to a {@link com.shoppingcart.auth.domain.entity.User}.
 *
 * <p>Valid values: {@code USER} (default upon registration) and {@code ADMIN} (elevated via
 * {@link com.shoppingcart.auth.domain.entity.User#promoteToAdmin()}).</p>
 *
 * <p>The static factory {@link #from(String)} converts an arbitrary string to a {@code Role},
 * throwing {@link InvalidRoleException} for any value not matching these two constants.</p>
 */
public enum Role {
    USER,
    ADMIN;

    /**
     * Converts a string to a {@code Role}, ignoring case.
     *
     * @param value the string to parse (e.g. {@code "user"}, {@code "ADMIN"})
     * @return the matching {@code Role} constant
     * @throws InvalidRoleException if {@code value} does not match {@code USER} or {@code ADMIN}
     */
    public static Role from(String value) {
        try {
            return Role.valueOf(value.toUpperCase());
        } catch (Exception e) {
            throw new InvalidRoleException("Invalid role: " + value + ". Use USER or ADMIN");
        }
    }
}