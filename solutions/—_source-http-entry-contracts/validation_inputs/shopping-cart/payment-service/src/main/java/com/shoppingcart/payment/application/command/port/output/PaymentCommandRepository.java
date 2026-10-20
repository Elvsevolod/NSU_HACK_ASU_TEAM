package com.shoppingcart.payment.application.command.port.output;

import com.shoppingcart.payment.domain.entity.Payment;

/**
 * Output port defining the write-side persistence contract for command use cases.
 *
 * <p>Exposes only the operations needed by command use cases, keeping the persistence
 * contract minimal and intention-revealing. The framework layer provides the implementation
 * via {@link com.shoppingcart.payment.framework.output.persistence.adapters.PaymentPersistenceAdapter}.</p>
 */
public interface PaymentCommandRepository {

    /**
     * Persists a new payment or updates an existing one.
     *
     * @param payment the payment to save
     * @return the saved {@link Payment}, potentially with a database-assigned ID
     */
    Payment save(Payment payment);

    /**
     * Looks up a payment by its identifier.
     *
     * @param id the numeric identifier of the payment
     * @return the matching {@link Payment}
     * @throws com.shoppingcart.payment.domain.exceptions.PaymentNotFoundException if no payment exists for {@code id}
     */
    Payment findById(Long id);

    /**
     * Checks whether an active ({@code PENDING} or {@code APPROVED}) payment already exists for the given order.
     *
     * @param orderId the identifier of the order to check
     * @return {@code true} if an active payment exists, {@code false} otherwise
     */
    boolean existsActivePaymentForOrder(Long orderId);
}
