package com.shoppingcart.payment.application.command.port.input;

import com.shoppingcart.payment.domain.entity.Payment;

/**
 * Input port for the refund-payment use case.
 *
 * <p>Defines the driving-side contract that input adapters (e.g., REST controller) use to
 * refund an approved payment. The implementation is provided by
 * {@link com.shoppingcart.payment.application.command.service.PaymentCommandService}.</p>
 */
public interface RefundPayment {

    /**
     * Refunds the payment identified by the given ID and reverts the associated order to pending.
     *
     * @param paymentId the numeric identifier of the payment to refund
     * @return the updated {@link Payment} with {@code REFUNDED} status
     * @throws com.shoppingcart.payment.domain.exceptions.PaymentNotFoundException        if no payment exists for {@code paymentId}
     * @throws com.shoppingcart.payment.domain.exceptions.PaymentAlreadyProcessedException if the payment is not in {@code APPROVED} status
     */
    Payment refund(Long paymentId);
}
