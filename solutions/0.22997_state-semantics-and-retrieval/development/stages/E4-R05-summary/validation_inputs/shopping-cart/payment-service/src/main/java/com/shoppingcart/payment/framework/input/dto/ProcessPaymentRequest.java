package com.shoppingcart.payment.framework.input.dto;

import java.math.BigDecimal;

import com.shoppingcart.payment.domain.vo.PaymentMethod;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

/**
 * HTTP request body for the process-payment endpoint ({@code POST /api/payments}).
 *
 * <p>All fields are validated with Bean Validation annotations before the controller
 * forwards the request to the application layer.</p>
 *
 * @param orderId       the identifier of the order to pay; must not be null
 * @param customerId    the identifier of the customer making the payment; must not be null
 * @param amount        the payment amount; must be greater than zero
 * @param paymentMethod the payment method chosen by the customer; must not be null
 */
public record ProcessPaymentRequest(
    @NotNull(message = "Order id is required")
    Long orderId,

    @NotNull(message = "Customer id is required")
    Long customerId,

    @NotNull(message = "Amount is required")
    @Positive(message = "Amount must be greater than zero")
    BigDecimal amount,

    @NotNull(message = "Payment method is required")
    PaymentMethod paymentMethod
) {}
