package com.shoppingcart.payment.application.command.dto;
import java.math.BigDecimal;
import com.shoppingcart.payment.domain.vo.PaymentMethod;

/**
 * Immutable command object carrying all data required to process a new payment.
 *
 * <p>Produced by the input adapter (REST controller) and consumed by
 * {@link com.shoppingcart.payment.application.command.port.input.ProcessPayment}.
 * It crosses the boundary between the framework and the application layer.</p>
 *
 * @param orderId       the identifier of the order to be paid
 * @param customerId    the identifier of the customer initiating the payment
 * @param amount        the payment amount; must match the order total
 * @param paymentMethod the method chosen by the customer for this payment
 */
public record ProcessPaymentCommand(
    Long orderId,
    Long customerId,
    BigDecimal amount,
    PaymentMethod paymentMethod
) {}



