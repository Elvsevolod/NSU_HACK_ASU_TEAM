package com.shoppingcart.payment.application.query.port.input;

import java.util.List;

import com.shoppingcart.payment.domain.entity.Payment;

/**
 * Input port for the get-payments-by-order query.
 *
 * <p>Defines the read-side contract that input adapters (e.g., REST controller) use to
 * retrieve all payments associated with a specific order. The implementation is provided by
 * {@link com.shoppingcart.payment.application.query.service.PaymentQueryService}.</p>
 */
public interface GetPaymentsByOrder {

    /**
     * Returns all payments associated with the given order.
     *
     * @param orderId the identifier of the order whose payments are to be retrieved
     * @return a (possibly empty) list of {@link Payment} objects for the order
     */
    List<Payment> getByOrderId(Long orderId);
}
