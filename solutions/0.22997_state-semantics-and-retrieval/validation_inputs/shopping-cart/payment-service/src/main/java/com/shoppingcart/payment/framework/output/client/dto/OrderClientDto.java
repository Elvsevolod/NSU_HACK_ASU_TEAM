package com.shoppingcart.payment.framework.output.client.dto;

import java.math.BigDecimal;

/**
 * Data Transfer Object representing the relevant fields of an order response from the order-service.
 *
 * <p>Contains only the fields required by the payment-service: the order ID, customer ID,
 * current status (for payability validation), and total amount (for amount matching).
 * This record is internal to the framework layer and must not leak into the application
 * or domain layers.</p>
 *
 * @param id         the order's unique identifier
 * @param customerId the identifier of the customer who placed the order
 * @param status     the current order status (e.g., "PENDING", "PAID", "CANCELLED")
 * @param total      the total monetary amount of the order
 */
public record OrderClientDto(
        Long id,
        Long customerId,
        String status,
        BigDecimal total
) {}
