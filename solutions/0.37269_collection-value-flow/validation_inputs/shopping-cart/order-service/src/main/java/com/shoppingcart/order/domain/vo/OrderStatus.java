package com.shoppingcart.order.domain.vo;

/**
 * Represents the lifecycle status of an {@link com.shoppingcart.order.domain.entity.Order}.
 *
 * <p>Valid transitions are enforced by the {@code Order} aggregate root:</p>
 * <ul>
 *   <li>{@code PENDING} → {@code CONFIRMED}, {@code CANCELLED}, or {@code PAID}</li>
 *   <li>{@code CONFIRMED} → {@code CANCELLED} or {@code PAID}</li>
 *   <li>{@code PAID} → {@code PENDING} (revert after payment failure)</li>
 *   <li>{@code CANCELLED} is a terminal state</li>
 * </ul>
 */
public enum OrderStatus {

    /** The order has been created and is awaiting confirmation or payment. */
    PENDING,

    /** The order has been confirmed and is ready to be fulfilled. */
    CONFIRMED,

    /** The order has been cancelled and can no longer be modified. */
    CANCELLED,

    /** The order has been successfully paid. */
    PAID
}
