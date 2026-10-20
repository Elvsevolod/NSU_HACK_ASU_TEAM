package com.shoppingcart.order.application.query.usecase;

import java.util.List;

import com.shoppingcart.order.application.query.port.output.OrderQueryRepository;
import com.shoppingcart.order.domain.entity.Order;

/**
 * Use case responsible for listing all orders that belong to a specific customer.
 *
 * <p>Delegates directly to the read-only repository port. Returns an empty list when the
 * customer has no orders; it does not throw if the customer ID is unknown.</p>
 */
public class ListOrdersByCustomerUseCase {

    private final OrderQueryRepository orderQueryRepository;

    /**
     * @param orderQueryRepository the read-only persistence port used to fetch orders
     */
    public ListOrdersByCustomerUseCase(OrderQueryRepository orderQueryRepository) {
        this.orderQueryRepository = orderQueryRepository;
    }

    /**
     * Executes the list-by-customer query.
     *
     * @param customerId the identifier of the customer whose orders are to be returned
     * @return a (possibly empty) list of {@link Order} objects belonging to the customer
     */
    public List<Order> execute(Long customerId) {
        return orderQueryRepository.findByCustomerId(customerId);
    }
}
