package com.shoppingcart.product.domain.vo;

import java.math.BigDecimal;
import java.math.RoundingMode;

import com.shoppingcart.product.domain.exceptions.ProductValidationException;

/**
 * Value object representing a monetary amount.
 * 
 * This record encapsulates a BigDecimal amount and ensures data integrity through
 * validation in the compact constructor. Money amounts are always validated to be
 * non-negative and scaled to 2 decimal places for proper currency representation.
 * 
 * @param amount the monetary amount in BigDecimal format (must not be null and >= 0)
 */
public record Money(BigDecimal amount) {

    public Money {
        if (amount == null)
            throw new ProductValidationException("price", "no puede ser nulo");
        if (amount.compareTo(BigDecimal.ZERO) < 0)
            throw new ProductValidationException("price", "no puede ser negativo");
        amount = amount.setScale(2, RoundingMode.HALF_UP);
    }

    /**
     * Factory method to create a Money instance from a double value.
     * 
     * @param value the monetary amount as a double
     * @return a new Money instance with the specified amount
     */
    public static Money of(double value) {
        return new Money(BigDecimal.valueOf(value));
    }

    /**
     * Compares this Money amount with another Money amount.
     * 
     * @param other the Money instance to compare with
     * @return true if this amount is greater than the other amount, false otherwise
     */
    public boolean isGreaterThan(Money other) {
        return this.amount.compareTo(other.amount) > 0;
    }
}
