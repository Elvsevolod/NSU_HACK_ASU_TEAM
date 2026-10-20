package com.shoppingcart.order.application.query.usecase;

import com.shoppingcart.order.application.query.port.output.OrderQueryRepository;
import com.shoppingcart.order.domain.entity.Order;
import com.shoppingcart.order.domain.exceptions.OrderNotFoundException;
import com.shoppingcart.order.domain.vo.OrderId;

/**
 * Use case responsible for retrieving a single order by its identifier.
 *
 * <p>Wraps the raw ID in the {@link OrderId} value object, delegates the lookup to
 * the read-only repository port, and raises {@link OrderNotFoundException} when the
 * order does not exist.</p>
 */
public class GetOrderUseCase {

    private final OrderQueryRepository orderQueryRepository;

    /**
     * @param orderQueryRepository the read-only persistence port used to fetch the order
     */
    public GetOrderUseCase(OrderQueryRepository orderQueryRepository) {
        this.orderQueryRepository = orderQueryRepository;
    }

    /**
     * Executes the get-order query.
     *
     * @param orderId the numeric identifier of the order to retrieve
     * @return the matching {@link Order}
     * @throws OrderNotFoundException if no order is found for {@code orderId}
     */
    public Order execute(Long orderId) {
        OrderId id = new OrderId(orderId);
        return orderQueryRepository.findById(id)
                .orElseThrow(() -> new OrderNotFoundException(id));
    }
}
