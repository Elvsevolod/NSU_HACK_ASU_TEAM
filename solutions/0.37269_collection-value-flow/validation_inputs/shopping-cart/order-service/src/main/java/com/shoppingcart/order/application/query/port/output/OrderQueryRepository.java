package com.shoppingcart.order.application.query.port.output;

import java.util.List;
import java.util.Optional;

import com.shoppingcart.order.domain.entity.Order;
import com.shoppingcart.order.domain.vo.OrderId;

/**
 * Output port defining the read-only persistence contract for the query use cases.
 *
 * <p>Follows the CQRS separation: this port is used exclusively for reads and does not
 * expose any write operations. The framework layer provides the implementation
 * (e.g., a JPA adapter) keeping infrastructure concerns out of the application layer.</p>
 */
public interface OrderQueryRepository {

    /**
     * Looks up an order by its identifier.
     *
     * @param id the value object wrapping the numeric order ID
     * @return an {@link Optional} containing the order if found, or empty if not
     */
    Optional<Order> findById(OrderId id);

    /**
     * Returns all orders associated with the given customer.
     *
     * @param customerId the identifier of the customer
     * @return a (possibly empty) list of orders belonging to the customer
     */
    List<Order> findByCustomerId(Long customerId);
}
