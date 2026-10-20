package com.shoppingcart.order.application.command.port.input;

import com.shoppingcart.order.domain.entity.Order;

/**
 * Input port for the revert-order-to-pending use case.
 *
 * <p>Defines the driving-side contract used to roll back a paid order to {@code PENDING}
 * status, typically triggered after a payment gateway failure or reversal. The implementation
 * is provided by {@link com.shoppingcart.order.application.command.service.OrderCommandService}.</p>
 */
public interface RevertOrderToPending {

    /**
     * Reverts the order identified by the given ID from {@code PAID} back to {@code PENDING} status.
     *
     * @param orderId the numeric identifier of the order to revert
     * @return the updated {@link Order} with {@code PENDING} status
     * @throws com.shoppingcart.order.domain.exceptions.OrderNotFoundException if no order exists for {@code orderId}
     * @throws IllegalStateException                                            if the order is not currently in {@code PAID} status
     */
    Order revertToPending(Long orderId);
}
