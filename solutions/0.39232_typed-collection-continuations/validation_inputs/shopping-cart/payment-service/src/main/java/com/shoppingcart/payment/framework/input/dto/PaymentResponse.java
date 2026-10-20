package com.shoppingcart.payment.framework.input.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import com.shoppingcart.payment.domain.vo.PaymentMethod;
import com.shoppingcart.payment.domain.vo.PaymentStatus;

/**
 * HTTP response body representing a payment returned by the REST API.
 *
 * <p>Produced by {@link com.shoppingcart.payment.framework.input.mapper.PaymentHttpMapper#toResponse}
 * from a domain {@link com.shoppingcart.payment.domain.entity.Payment} aggregate.</p>
 *
 * @param id            the unique identifier of the payment
 * @param orderId       the identifier of the associated order
 * @param customerId    the identifier of the customer who initiated the payment
 * @param amount        the monetary amount of the payment
 * @param paymentMethod the payment method used
 * @param status        the current lifecycle status of the payment
 * @param createdAt     the timestamp when the payment was created
 */
public record PaymentResponse(
    Long id,
    Long orderId,
    Long customerId,
    BigDecimal amount,
    PaymentMethod paymentMethod,
    PaymentStatus status,
    LocalDateTime createdAt
){}