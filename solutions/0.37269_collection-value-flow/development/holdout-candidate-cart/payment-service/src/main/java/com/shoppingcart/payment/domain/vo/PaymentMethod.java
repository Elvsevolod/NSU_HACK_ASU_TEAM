package com.shoppingcart.payment.domain.vo;

/**
 * Represents the payment method chosen by the customer for a
 * {@link com.shoppingcart.payment.domain.entity.Payment}.
 */
public enum PaymentMethod {

    /** Payment via credit card. */
    CREDIT_CARD,

    /** Payment via debit card. */
    DEBIT_CARD,

    /** Payment with physical cash. */
    CASH,

    /** Payment via bank transfer. */
    TRANSFER
}
