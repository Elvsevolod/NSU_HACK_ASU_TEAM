package com.shoppingcart.payment.application.command.usecase;

import com.shoppingcart.payment.application.command.port.output.OrderStatusPort;
import com.shoppingcart.payment.application.command.port.output.PaymentCommandRepository;
import com.shoppingcart.payment.domain.entity.Payment;

/**
 * Use case responsible for refunding an approved payment.
 *
 * <p>Loads the payment, transitions it to {@code REFUNDED} via the domain method
 * {@link com.shoppingcart.payment.domain.entity.Payment#refund()}, persists the result,
 * and notifies the order-service to revert the order back to {@code PENDING}.</p>
 */
public class RefundPaymentUseCase {

    private final PaymentCommandRepository repository;
    private final OrderStatusPort orderStatusPort;

    /**
     * @param repository      the persistence port for loading and saving the payment
     * @param orderStatusPort the port for notifying the order-service of the refund
     */
    public RefundPaymentUseCase(PaymentCommandRepository repository, OrderStatusPort orderStatusPort) {
        this.repository = repository;
        this.orderStatusPort = orderStatusPort;
    }

    /**
     * Executes the refund-payment use case.
     *
     * @param paymentId the numeric identifier of the payment to refund
     * @return the persisted {@link com.shoppingcart.payment.domain.entity.Payment} with {@code REFUNDED} status
     * @throws com.shoppingcart.payment.domain.exceptions.PaymentNotFoundException        if no payment exists for {@code paymentId}
     * @throws com.shoppingcart.payment.domain.exceptions.PaymentAlreadyProcessedException if the payment is not in {@code APPROVED} status
     */
    public Payment execute(Long paymentId) {
        Payment payment = repository.findById(paymentId);
        payment = repository.save(payment.refund());
        orderStatusPort.revertToPending(payment.getOrderId());
        return payment;
    }
}
