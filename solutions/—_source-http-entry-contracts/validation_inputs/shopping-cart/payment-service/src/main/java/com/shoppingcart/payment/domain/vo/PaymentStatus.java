package com.shoppingcart.payment.domain.vo;

/**
 * Represents the lifecycle status of a {@link com.shoppingcart.payment.domain.entity.Payment}.
 *
 * <p>Valid transitions enforced by the {@code Payment} aggregate:</p>
 * <ul>
 *   <li>{@code PENDING} → {@code APPROVED} or {@code REJECTED}</li>
 *   <li>{@code APPROVED} → {@code REFUNDED}</li>
 *   <li>{@code REJECTED} and {@code REFUNDED} are terminal states</li>
 * </ul>
 */
public enum PaymentStatus {

    /** The payment has been created and is awaiting processing. */
    PENDING,

    /** The payment was successfully processed and the order is considered paid. */
    APPROVED,

    /** The payment was declined during processing (simulated rejection). */
    REJECTED,

    /** The payment was refunded and the order has been reverted to pending. */
    REFUNDED
}
