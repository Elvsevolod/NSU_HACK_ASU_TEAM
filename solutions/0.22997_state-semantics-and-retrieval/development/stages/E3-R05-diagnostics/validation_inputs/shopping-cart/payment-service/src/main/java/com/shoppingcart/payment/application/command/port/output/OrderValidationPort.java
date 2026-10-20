package com.shoppingcart.payment.application.command.port.output;

import com.shoppingcart.payment.framework.output.client.dto.OrderClientDto;

/**
 * Output port for fetching and validating an order from the order-service before processing a payment.
 *
 * <p>The implementation checks that the order exists and is in a payable state
 * (not {@code CANCELLED} or {@code PAID}). The framework layer provides the concrete adapter
 * ({@link com.shoppingcart.payment.framework.output.client.adapters.OrderClientAdapter}).</p>
 */
public interface OrderValidationPort {

    /**
     * Retrieves the order from the order-service and validates that it is eligible for payment.
     *
     * @param orderId the identifier of the order to validate
     * @return the order data as an {@link com.shoppingcart.payment.framework.output.client.dto.OrderClientDto}
     * @throws com.shoppingcart.payment.domain.exceptions.OrderNotFoundException          if the order does not exist
     * @throws com.shoppingcart.payment.domain.exceptions.OrderNotValidForPaymentException if the order is in a non-payable status
     */
    OrderClientDto getOrderIfValid(Long orderId);
}
