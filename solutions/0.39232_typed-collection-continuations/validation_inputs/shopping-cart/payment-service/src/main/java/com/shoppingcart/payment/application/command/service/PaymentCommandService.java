package com.shoppingcart.payment.application.command.service;

import com.shoppingcart.payment.application.command.dto.ProcessPaymentCommand;
import com.shoppingcart.payment.application.command.port.input.ProcessPayment;
import com.shoppingcart.payment.application.command.port.input.RefundPayment;
import com.shoppingcart.payment.application.command.port.output.OrderStatusPort;
import com.shoppingcart.payment.application.command.port.output.OrderValidationPort;
import com.shoppingcart.payment.application.command.port.output.PaymentCommandRepository;
import com.shoppingcart.payment.application.command.usecase.ProcessPaymentUseCase;
import com.shoppingcart.payment.application.command.usecase.RefundPaymentUseCase;
import com.shoppingcart.payment.domain.entity.Payment;

/**
 * Application service that fulfills all write-side (command) input ports for payments.
 *
 * <p>Acts as the single entry point for all payment-mutating operations, delegating each
 * operation to a dedicated use-case class. Provides two constructors to support both
 * direct use-case injection (for testing) and automatic wiring from output ports (production).</p>
 *
 * <p>Implements:</p>
 * <ul>
 *   <li>{@link ProcessPayment}</li>
 *   <li>{@link RefundPayment}</li>
 * </ul>
 */
public class PaymentCommandService implements ProcessPayment, RefundPayment {

    private final ProcessPaymentUseCase processUseCase;
    private final RefundPaymentUseCase refundUseCase;

    /**
     * Constructor for direct use-case injection (useful for testing).
     *
     * @param processUseCase the use case for processing payments
     * @param refundUseCase  the use case for refunding payments
     */
    public PaymentCommandService(ProcessPaymentUseCase processUseCase, RefundPaymentUseCase refundUseCase) {
        this.processUseCase = processUseCase;
        this.refundUseCase = refundUseCase;
    }

    /**
     * Constructor that wires use cases from output ports (used by Spring configuration).
     *
     * @param repository           the persistence port for saving and loading payments
     * @param orderValidationPort  the port for validating orders before payment
     * @param orderStatusPort      the port for notifying the order-service of payment outcomes
     */
    public PaymentCommandService(PaymentCommandRepository repository,
            OrderValidationPort orderValidationPort, OrderStatusPort orderStatusPort) {
        this.processUseCase = new ProcessPaymentUseCase(repository, orderValidationPort, orderStatusPort);
        this.refundUseCase = new RefundPaymentUseCase(repository, orderStatusPort);
    }

    /** {@inheritDoc} */
    @Override
    public Payment process(ProcessPaymentCommand command) {
        return processUseCase.execute(command);
    }

    /** {@inheritDoc} */
    @Override
    public Payment refund(Long paymentId) {
        return refundUseCase.execute(paymentId);
    }
}
