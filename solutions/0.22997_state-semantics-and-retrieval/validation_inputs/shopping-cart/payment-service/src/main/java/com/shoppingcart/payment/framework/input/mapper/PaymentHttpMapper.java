package com.shoppingcart.payment.framework.input.mapper;

import com.shoppingcart.payment.application.command.dto.ProcessPaymentCommand;
import com.shoppingcart.payment.domain.entity.Payment;
import com.shoppingcart.payment.framework.input.dto.PaymentResponse;
import com.shoppingcart.payment.framework.input.dto.ProcessPaymentRequest;

/**
 * Stateless mapper that converts between HTTP-layer DTOs and application-layer objects.
 *
 * <p>All methods are static; this class is not meant to be instantiated.</p>
 */
public class PaymentHttpMapper {

    private PaymentHttpMapper() {}

    /**
     * Converts an HTTP request body into an application-layer command.
     *
     * @param request the validated incoming HTTP request
     * @return a {@link ProcessPaymentCommand} ready to be passed to the input port
     */
    public static ProcessPaymentCommand toCommand(ProcessPaymentRequest request) {
        return new ProcessPaymentCommand(
            request.orderId(),
            request.customerId(),
            request.amount(),
            request.paymentMethod()
        );
    }

    /**
     * Converts a domain {@link Payment} aggregate into an HTTP response body.
     *
     * @param payment the domain payment to serialize
     * @return a {@link PaymentResponse} suitable for JSON serialization
     */
    public static PaymentResponse toResponse(Payment payment) {
        return new PaymentResponse(
            payment.getId(),
            payment.getOrderId(),
            payment.getCustomerId(),
            payment.getAmount(),
            payment.getPaymentMethod(),
            payment.getStatus(),
            payment.getCreatedAt()
        );
    }
}

