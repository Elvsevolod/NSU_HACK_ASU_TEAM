package com.shoppingcart.order.application.command.port.input;

import com.shoppingcart.order.domain.entity.Order;

/**
 * Input port for the cancel-order use case.
 *
 * <p>Defines the driving-side contract that input adapters (e.g., REST controllers) use to
 * cancel an existing order. The implementation is provided by
 * {@link com.shoppingcart.order.application.command.service.OrderCommandService}.</p>
 */
public interface CancelOrder {

    /**
     * Cancels the order identified by the given ID.
     *
     * @param orderId the numeric identifier of the order to cancel
     * @return the updated {@link Order} with {@code CANCELLED} status
     * @throws com.shoppingcart.order.domain.exceptions.OrderNotFoundException        if no order exists for {@code orderId}
     * @throws com.shoppingcart.order.domain.exceptions.OrderAlreadyCancelledException if the order is already cancelled
     * @throws IllegalStateException                                                   if the order is in {@code PAID} status
     */
    Order cancel(Long orderId);
}
