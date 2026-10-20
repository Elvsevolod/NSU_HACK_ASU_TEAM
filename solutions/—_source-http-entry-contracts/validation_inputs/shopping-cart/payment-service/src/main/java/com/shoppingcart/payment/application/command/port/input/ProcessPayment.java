package com.shoppingcart.payment.application.command.port.input;

import com.shoppingcart.payment.application.command.dto.ProcessPaymentCommand;
import com.shoppingcart.payment.domain.entity.Payment;

/**
 * Input port for the process-payment use case.
 *
 * <p>Defines the driving-side contract that input adapters (e.g., REST controller) use to
 * initiate a payment. The implementation is provided by
 * {@link com.shoppingcart.payment.application.command.service.PaymentCommandService}.</p>
 */
public interface ProcessPayment {

    /**
     * Processes a payment for the order specified in the command.
     *
     * <p>Validates the order, checks for duplicate payments, simulates processing,
     * and notifies the order-service of the result.</p>
     *
     * @param command the command carrying order, customer, amount, and method data
     * @return the persisted {@link Payment} with its final status ({@code APPROVED} or {@code REJECTED})
     * @throws com.shoppingcart.payment.domain.exceptions.OrderNotFoundException          if the order does not exist
     * @throws com.shoppingcart.payment.domain.exceptions.OrderNotValidForPaymentException if the order is not in a payable state
     * @throws com.shoppingcart.payment.domain.exceptions.OrderAlreadyPaidException       if an active payment already exists for the order
     * @throws com.shoppingcart.payment.domain.exceptions.InvalidPaymentAmountException   if the amount does not match the order total
     */
    Payment process(ProcessPaymentCommand command);
}
