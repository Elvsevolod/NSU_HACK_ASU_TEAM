package com.shoppingcart.order.application.command.usecase;

import com.shoppingcart.order.application.command.port.output.OrderCommandRepository;
import com.shoppingcart.order.domain.entity.Order;
import com.shoppingcart.order.domain.exceptions.OrderNotFoundException;
import com.shoppingcart.order.domain.vo.OrderId;

/**
 * Use case responsible for cancelling an existing order.
 *
 * <p>Loads the order from the repository, delegates the state transition to the domain
 * aggregate ({@link Order#cancel()}), and persists the updated order. All business rules
 * around cancellation (e.g., cannot cancel a paid order) are enforced by the domain layer.</p>
 */
public class CancelOrderUseCase {

    private final OrderCommandRepository orderCommandRepository;

    /**
     * @param orderCommandRepository the persistence port used to load and save the order
     */
    public CancelOrderUseCase(OrderCommandRepository orderCommandRepository) {
        this.orderCommandRepository = orderCommandRepository;
    }

    /**
     * Executes the cancel-order use case.
     *
     * @param orderId the numeric identifier of the order to cancel
     * @return the persisted {@link Order} with {@code CANCELLED} status
     * @throws OrderNotFoundException        if no order is found for {@code orderId}
     * @throws com.shoppingcart.order.domain.exceptions.OrderAlreadyCancelledException if the order is already cancelled
     * @throws IllegalStateException         if the order is in {@code PAID} status
     */
    public Order execute(Long orderId) {
        OrderId id = new OrderId(orderId);
        Order order = orderCommandRepository.findById(id)
                .orElseThrow(() -> new OrderNotFoundException(id));
        order.cancel();
        return orderCommandRepository.save(order);
    }
}
