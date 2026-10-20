package com.shoppingcart.order.application.query.port.input;

import java.util.List;

import com.shoppingcart.order.domain.entity.Order;

/**
 * Input port for the list-orders-by-customer query.
 *
 * <p>Defines the read-side contract that input adapters (e.g., REST controllers) use to
 * retrieve all orders belonging to a specific customer. The implementation is provided by
 * {@link com.shoppingcart.order.application.query.service.OrderQueryService}.</p>
 */
public interface ListOrdersByCustomer {

    /**
     * Returns all orders associated with the given customer.
     *
     * @param customerId the identifier of the customer whose orders are to be retrieved
     * @return a (possibly empty) list of {@link Order} objects belonging to the customer
     */
    List<Order> listByCustomer(Long customerId);
}
