package com.shoppingcart.payment.application.command.usecase;

import com.shoppingcart.payment.application.command.dto.ProcessPaymentCommand;
import com.shoppingcart.payment.application.command.port.output.OrderStatusPort;
import com.shoppingcart.payment.application.command.port.output.OrderValidationPort;
import com.shoppingcart.payment.application.command.port.output.PaymentCommandRepository;
import com.shoppingcart.payment.domain.entity.Payment;
import com.shoppingcart.payment.domain.exceptions.InvalidPaymentAmountException;
import com.shoppingcart.payment.domain.exceptions.OrderAlreadyPaidException;
import com.shoppingcart.payment.framework.output.client.dto.OrderClientDto;

/**
 * Use case responsible for processing a payment for an order.
 *
 * <p>Orchestrates the following steps:</p>
 * <ol>
 *   <li>Validates that the order exists and is in a payable state via {@link OrderValidationPort}.</li>
 *   <li>Verifies that the supplied amount matches the order total.</li>
 *   <li>Checks that no active payment already exists for the order.</li>
 *   <li>Creates the {@link Payment} domain object in {@code PENDING} status.</li>
 *   <li>Simulates processing: approves with 80% probability, rejects otherwise.</li>
 *   <li>Persists the payment result.</li>
 *   <li>If approved, notifies the order-service via {@link OrderStatusPort#markAsPaid}.</li>
 * </ol>
 */
public class ProcessPaymentUseCase {

    private final PaymentCommandRepository repository;
    private final OrderValidationPort orderValidationPort;
    private final OrderStatusPort orderStatusPort;

    /**
     * @param repository          the persistence port for saving the payment
     * @param orderValidationPort the port for fetching and validating the order
     * @param orderStatusPort     the port for notifying the order-service after processing
     */
    public ProcessPaymentUseCase(PaymentCommandRepository repository,
            OrderValidationPort orderValidationPort, OrderStatusPort orderStatusPort) {
        this.repository = repository;
        this.orderValidationPort = orderValidationPort;
        this.orderStatusPort = orderStatusPort;
    }

    /**
     * Executes the process-payment use case.
     *
     * @param command the command carrying order, customer, amount, and payment method
     * @return the persisted {@link Payment} with status {@code APPROVED} or {@code REJECTED}
     * @throws com.shoppingcart.payment.domain.exceptions.OrderNotFoundException          if the order does not exist
     * @throws com.shoppingcart.payment.domain.exceptions.OrderNotValidForPaymentException if the order is not payable
     * @throws com.shoppingcart.payment.domain.exceptions.InvalidPaymentAmountException   if the amount differs from the order total
     * @throws com.shoppingcart.payment.domain.exceptions.OrderAlreadyPaidException       if an active payment already exists
     */
    public Payment execute(ProcessPaymentCommand command) {
        OrderClientDto order = orderValidationPort.getOrderIfValid(command.orderId());

        if (order.total().compareTo(command.amount()) != 0)
            throw new InvalidPaymentAmountException(order.total(), command.amount());

        if (repository.existsActivePaymentForOrder(command.orderId()))
            throw new OrderAlreadyPaidException(command.orderId());

        Payment payment = Payment.create(
                command.orderId(), command.customerId(),
                command.amount(), command.paymentMethod());

        // Simulate payment: 80% approval rate
        boolean approved = Math.random() < 0.8;
        payment = approved ? payment.approve() : payment.reject();
        payment = repository.save(payment);

        if (payment.getStatus().name().equals("APPROVED"))
            orderStatusPort.markAsPaid(command.orderId());

        return payment;
    }
}
