package com.shoppingcart.payment.application.query.port.output;

import java.util.List;

import com.shoppingcart.payment.domain.entity.Payment;

/**
 * Output port defining the read-only persistence contract for query use cases.
 *
 * <p>Follows CQRS separation: this port is used exclusively for reads and does not expose
 * any write operations. The framework layer provides the implementation via
 * {@link com.shoppingcart.payment.framework.output.persistence.adapters.PaymentPersistenceAdapter}.</p>
 */
public interface PaymentQueryRepository {

    /**
     * Looks up a payment by its identifier.
     *
     * @param id the numeric identifier of the payment
     * @return the matching {@link Payment}
     * @throws com.shoppingcart.payment.domain.exceptions.PaymentNotFoundException if no payment exists for {@code id}
     */
    Payment findById(Long id);

    /**
     * Returns all payments associated with the given order.
     *
     * @param orderId the identifier of the order
     * @return a (possibly empty) list of payments for the order
     */
    List<Payment> findByOrderId(Long orderId);
}
