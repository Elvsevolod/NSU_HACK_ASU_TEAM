package com.shoppingcart.order.application.query.port.input;

import com.shoppingcart.order.domain.entity.Order;

/**
 * Input port for the get-order-by-ID query.
 *
 * <p>Defines the read-side contract that input adapters (e.g., REST controllers) use to
 * fetch a single order. The implementation is provided by
 * {@link com.shoppingcart.order.application.query.service.OrderQueryService}.</p>
 */
public interface GetOrder {

    /**
     * Retrieves a single order by its numeric identifier.
     *
     * @param orderId the identifier of the order to retrieve
     * @return the matching {@link Order}
     * @throws com.shoppingcart.order.domain.exceptions.OrderNotFoundException if no order exists for {@code orderId}
     */
    Order getById(Long orderId);
}
