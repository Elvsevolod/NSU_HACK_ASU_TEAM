package com.shoppingcart.payment.application.query.usecase;

import com.shoppingcart.payment.application.query.port.output.PaymentQueryRepository;
import com.shoppingcart.payment.domain.entity.Payment;

/**
 * Use case responsible for retrieving a single payment by its identifier.
 *
 * <p>Delegates directly to the read-only repository port and propagates
 * {@link com.shoppingcart.payment.domain.exceptions.PaymentNotFoundException}
 * if no matching record exists.</p>
 */
public class GetPaymentUseCase {

    private final PaymentQueryRepository repository;

    /**
     * @param repository the read-only persistence port used to fetch the payment
     */
    public GetPaymentUseCase(PaymentQueryRepository repository) {
        this.repository = repository;
    }

    /**
     * Executes the get-payment query.
     *
     * @param id the numeric identifier of the payment to retrieve
     * @return the matching {@link Payment}
     * @throws com.shoppingcart.payment.domain.exceptions.PaymentNotFoundException if no payment exists for {@code id}
     */
    public Payment execute(Long id) {
        return repository.findById(id);
    }
}
