package com.shoppingcart.payment.application.query.port.input;

import com.shoppingcart.payment.domain.entity.Payment;

/**
 * Input port for the get-payment-by-ID query.
 *
 * <p>Defines the read-side contract that input adapters (e.g., REST controller) use to
 * fetch a single payment. The implementation is provided by
 * {@link com.shoppingcart.payment.application.query.service.PaymentQueryService}.</p>
 */
public interface GetPayment {

    /**
     * Retrieves a single payment by its numeric identifier.
     *
     * @param id the identifier of the payment to retrieve
     * @return the matching {@link Payment}
     * @throws com.shoppingcart.payment.domain.exceptions.PaymentNotFoundException if no payment exists for {@code id}
     */
    Payment getById(Long id);
}
