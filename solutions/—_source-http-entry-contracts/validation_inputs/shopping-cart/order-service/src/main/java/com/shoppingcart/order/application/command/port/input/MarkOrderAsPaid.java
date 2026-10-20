package com.shoppingcart.order.application.command.port.input;

import com.shoppingcart.order.domain.entity.Order;

/**
 * Input port for the mark-order-as-paid use case.
 *
 * <p>Defines the driving-side contract that input adapters (e.g., the payment service callback)
 * use to record a successful payment. The implementation is provided by
 * {@link com.shoppingcart.order.application.command.service.OrderCommandService}.</p>
 */
public interface MarkOrderAsPaid {

    /**
     * Transitions the order identified by the given ID to {@code PAID} status.
     *
     * @param orderId the numeric identifier of the order to mark as paid
     * @return the updated {@link Order} with {@code PAID} status
     * @throws com.shoppingcart.order.domain.exceptions.OrderNotFoundException if no order exists for {@code orderId}
     * @throws IllegalStateException                                            if the order is not in {@code PENDING} or {@code CONFIRMED} status
     */
    Order markAsPaid(Long orderId);
}
