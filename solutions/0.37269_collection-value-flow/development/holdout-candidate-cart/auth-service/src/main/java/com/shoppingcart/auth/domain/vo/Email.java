package com.shoppingcart.auth.domain.vo;

import com.shoppingcart.auth.domain.exception.InvalidEmailException;

/**
 * Value object representing a validated, normalised e-mail address.
 *
 * <p>The compact constructor enforces a simple regex pattern and normalises the value to
 * lower-case with surrounding whitespace removed before the record field is assigned.
 * Throws {@link InvalidEmailException} immediately if the address is {@code null} or does
 * not match {@code ^[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}$}.</p>
 */
public record Email(String value) {

    /**
     * Validates and normalises the e-mail address.
     *
     * @throws InvalidEmailException if {@code value} is {@code null} or does not match the expected format
     */
    public Email {
        if (value == null || !value.matches("^[\\w.-]+@[\\w.-]+\\.[a-zA-Z]{2,}$"))
            throw new InvalidEmailException("Invalid email: " + value);
        value = value.toLowerCase().trim();
    }
}