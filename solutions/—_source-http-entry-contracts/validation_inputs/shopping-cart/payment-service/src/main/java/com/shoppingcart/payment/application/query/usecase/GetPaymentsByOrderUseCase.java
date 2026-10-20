package com.shoppingcart.payment.application.query.usecase;

import java.util.List;

import com.shoppingcart.payment.application.query.port.output.PaymentQueryRepository;
import com.shoppingcart.payment.domain.entity.Payment;

/**
 * Use case responsible for listing all payments associated with a specific order.
 *
 * <p>Delegates directly to the read-only repository port. Returns an empty list
 * when no payments exist for the given order; it does not throw if the order ID is unknown.</p>
 */
public class GetPaymentsByOrderUseCase {

    private final PaymentQueryRepository repository;

    /**
     * @param repository the read-only persistence port used to fetch payments
     */
    public GetPaymentsByOrderUseCase(PaymentQueryRepository repository) {
        this.repository = repository;
    }

    /**
     * Executes the get-payments-by-order query.
     *
     * @param orderId the identifier of the order whose payments are to be returned
     * @return a (possibly empty) list of {@link Payment} objects for the order
     */
    public List<Payment> execute(Long orderId) {
        return repository.findByOrderId(orderId);
    }
}
