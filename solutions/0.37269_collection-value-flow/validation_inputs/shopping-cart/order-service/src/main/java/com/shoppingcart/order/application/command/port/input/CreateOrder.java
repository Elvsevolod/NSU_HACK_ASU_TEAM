package com.shoppingcart.order.application.command.port.input;

import com.shoppingcart.order.application.command.dto.CreateOrderCommand;
import com.shoppingcart.order.domain.entity.Order;

/**
 * Input port for the create-order use case.
 *
 * <p>Defines the driving-side contract that input adapters (e.g., REST controllers) use to
 * place a new order. The implementation is provided by
 * {@link com.shoppingcart.order.application.command.service.OrderCommandService}.</p>
 */
public interface CreateOrder {

    /**
     * Creates and persists a new order from the given command.
     *
     * <p>Each line item's price is validated against the product catalog before the order
     * is saved. The order starts in {@code PENDING} status.</p>
     *
     * @param command the command carrying customer and product line-item data
     * @return the newly created and persisted {@link Order}
     * @throws com.shoppingcart.order.domain.exceptions.PriceMismatchException  if any line item's price deviates from the catalog price
     * @throws com.shoppingcart.order.domain.exceptions.InvalidProductException if a referenced product does not exist or is unavailable
     * @throws IllegalArgumentException                                          if the command contains no line items
     */
    Order create(CreateOrderCommand command);
}
