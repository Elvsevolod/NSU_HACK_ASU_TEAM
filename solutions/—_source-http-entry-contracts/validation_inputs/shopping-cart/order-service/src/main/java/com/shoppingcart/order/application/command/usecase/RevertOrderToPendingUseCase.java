package com.shoppingcart.order.application.command.usecase;

import com.shoppingcart.order.application.command.port.output.OrderCommandRepository;
import com.shoppingcart.order.domain.entity.Order;
import com.shoppingcart.order.domain.exceptions.OrderNotFoundException;
import com.shoppingcart.order.domain.vo.OrderId;

/**
 * Use case responsible for reverting a paid order back to {@code PENDING} status.
 *
 * <p>Intended for payment-rollback scenarios (e.g., a gateway reversal or chargeback).
 * Loads the order, delegates the state transition to the domain aggregate
 * ({@link Order#revertToPending()}), and persists the result. Only orders in {@code PAID}
 * status can be reverted; the domain enforces this invariant.</p>
 */
public class RevertOrderToPendingUseCase {

    private final OrderCommandRepository orderCommandRepository;

    /**
     * @param orderCommandRepository the persistence port used to load and save the order
     */
    public RevertOrderToPendingUseCase(OrderCommandRepository orderCommandRepository) {
        this.orderCommandRepository = orderCommandRepository;
    }

    /**
     * Executes the revert-to-pending use case.
     *
     * @param orderId the numeric identifier of the order to revert
     * @return the persisted {@link Order} with {@code PENDING} status
     * @throws OrderNotFoundException if no order is found for {@code orderId}
     * @throws IllegalStateException  if the order is not in {@code PAID} status
     */
    public Order execute(Long orderId) {
        OrderId id = new OrderId(orderId);
        Order order = orderCommandRepository.findById(id)
                .orElseThrow(() -> new OrderNotFoundException(id));
        order.revertToPending();
        return orderCommandRepository.save(order);
    }
}
