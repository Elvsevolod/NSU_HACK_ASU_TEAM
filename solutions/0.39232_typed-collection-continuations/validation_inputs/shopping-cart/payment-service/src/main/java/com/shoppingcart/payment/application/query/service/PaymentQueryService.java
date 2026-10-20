package com.shoppingcart.payment.application.query.service;

import java.util.List;

import com.shoppingcart.payment.application.query.port.input.GetPayment;
import com.shoppingcart.payment.application.query.port.input.GetPaymentsByOrder;
import com.shoppingcart.payment.application.query.port.output.PaymentQueryRepository;
import com.shoppingcart.payment.application.query.usecase.GetPaymentUseCase;
import com.shoppingcart.payment.application.query.usecase.GetPaymentsByOrderUseCase;
import com.shoppingcart.payment.domain.entity.Payment;

/**
 * Application service that fulfills all read-side (query) input ports for payments.
 *
 * <p>Delegates each query to a dedicated use-case class, keeping concerns focused
 * and independently testable.</p>
 *
 * <p>Implements:</p>
 * <ul>
 *   <li>{@link GetPayment}</li>
 *   <li>{@link GetPaymentsByOrder}</li>
 * </ul>
 */
public class PaymentQueryService implements GetPayment, GetPaymentsByOrder {

    private final GetPaymentUseCase getUseCase;
    private final GetPaymentsByOrderUseCase getByOrderUseCase;

    /**
     * Constructs the service and wires each use case with the required repository port.
     *
     * @param repository the read-only persistence port for loading payments
     */
    public PaymentQueryService(PaymentQueryRepository repository) {
        this.getUseCase = new GetPaymentUseCase(repository);
        this.getByOrderUseCase = new GetPaymentsByOrderUseCase(repository);
    }

    /** {@inheritDoc} */
    public Payment getById(Long id) {
        return getUseCase.execute(id);
    }

    /** {@inheritDoc} */
    public List<Payment> getByOrderId(Long orderId) {
        return getByOrderUseCase.execute(orderId);
    }
}
