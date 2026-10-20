package com.shoppingcart.order.application.command.usecase;

import com.shoppingcart.order.application.command.port.output.OrderCommandRepository;
import com.shoppingcart.order.domain.entity.Order;
import com.shoppingcart.order.domain.exceptions.OrderNotFoundException;
import com.shoppingcart.order.domain.vo.OrderId;

/**
 * Use case responsible for recording a successful payment on an existing order.
 *
 * <p>Loads the order, delegates the state transition to the domain aggregate
 * ({@link Order#markAsPaid()}), and persists the result. Only orders in {@code PENDING}
 * or {@code CONFIRMED} status can be marked as paid; the domain enforces this invariant.</p>
 */
public class MarkOrderAsPaidUseCase {

    private final OrderCommandRepository orderCommandRepository;

    /**
     * @param orderCommandRepository the persistence port used to load and save the order
     */
    public MarkOrderAsPaidUseCase(OrderCommandRepository orderCommandRepository) {
        this.orderCommandRepository = orderCommandRepository;
    }

    /**
     * Executes the mark-as-paid use case.
     *
     * @param orderId the numeric identifier of the order to mark as paid
     * @return the persisted {@link Order} with {@code PAID} status
     * @throws OrderNotFoundException if no order is found for {@code orderId}
     * @throws IllegalStateException  if the order is not in {@code PENDING} or {@code CONFIRMED} status
     */
    public Order execute(Long orderId) {
        OrderId id = new OrderId(orderId);
        Order order = orderCommandRepository.findById(id)
                .orElseThrow(() -> new OrderNotFoundException(id));
        order.markAsPaid();
        return orderCommandRepository.save(order);
    }
}
