package com.shoppingcart.order.application.command.port.output;

import java.util.Optional;

import com.shoppingcart.order.domain.entity.Order;
import com.shoppingcart.order.domain.vo.OrderId;

/**
 * Output port defining the write-side persistence contract for the command use cases.
 *
 * <p>This interface is part of the hexagonal architecture driven boundary: the application layer
 * declares what it needs from persistence, and the framework layer provides the implementation
 * (e.g., a JPA adapter). It is intentionally kept minimal — only the operations needed by
 * command use cases are exposed here.</p>
 */
public interface OrderCommandRepository {

    /**
     * Looks up an order by its identifier.
     *
     * @param id the value object wrapping the numeric order ID
     * @return an {@link Optional} containing the order if found, or empty if not
     */
    Optional<Order> findById(OrderId id);

    /**
     * Persists a new order or updates an existing one.
     *
     * @param order the order aggregate to save
     * @return the saved {@link Order}, potentially with a database-assigned ID
     */
    Order save(Order order);
}
