package com.shoppingcart.order.application.command.service;

import com.shoppingcart.order.application.command.dto.CreateOrderCommand;
import com.shoppingcart.order.application.command.port.input.CancelOrder;
import com.shoppingcart.order.application.command.port.input.CreateOrder;
import com.shoppingcart.order.application.command.port.input.MarkOrderAsPaid;
import com.shoppingcart.order.application.command.port.input.RevertOrderToPending;
import com.shoppingcart.order.application.command.port.output.OrderCommandRepository;
import com.shoppingcart.order.application.command.port.output.ProductValidationPort;
import com.shoppingcart.order.application.command.usecase.CancelOrderUseCase;
import com.shoppingcart.order.application.command.usecase.CreateOrderUseCase;
import com.shoppingcart.order.application.command.usecase.MarkOrderAsPaidUseCase;
import com.shoppingcart.order.application.command.usecase.RevertOrderToPendingUseCase;
import com.shoppingcart.order.domain.entity.Order;

/**
 * Application service that fulfills all write-side (command) input ports.
 *
 * <p>Acts as the single entry point for all order-mutating operations. Rather than
 * implementing business logic directly, it instantiates and delegates to dedicated use-case
 * classes, keeping each operation focused and independently testable.</p>
 *
 * <p>Implements the following input ports:</p>
 * <ul>
 *   <li>{@link CreateOrder}</li>
 *   <li>{@link CancelOrder}</li>
 *   <li>{@link MarkOrderAsPaid}</li>
 *   <li>{@link RevertOrderToPending}</li>
 * </ul>
 */
public class OrderCommandService implements CreateOrder, CancelOrder, MarkOrderAsPaid, RevertOrderToPending {

    private final CreateOrderUseCase createOrderUseCase;
    private final CancelOrderUseCase cancelOrderUseCase;
    private final MarkOrderAsPaidUseCase markOrderAsPaidUseCase;
    private final RevertOrderToPendingUseCase revertOrderToPendingUseCase;

    /**
     * Constructs the service and wires each use case with the required output ports.
     *
     * @param orderCommandRepository  the persistence port for loading and saving orders
     * @param productValidationPort   the external port for validating product prices
     */
    public OrderCommandService(OrderCommandRepository orderCommandRepository,
            ProductValidationPort productValidationPort) {
        this.createOrderUseCase = new CreateOrderUseCase(orderCommandRepository, productValidationPort);
        this.cancelOrderUseCase = new CancelOrderUseCase(orderCommandRepository);
        this.markOrderAsPaidUseCase = new MarkOrderAsPaidUseCase(orderCommandRepository);
        this.revertOrderToPendingUseCase = new RevertOrderToPendingUseCase(orderCommandRepository);
    }

    /** {@inheritDoc} */
    @Override
    public Order create(CreateOrderCommand command) {
        return createOrderUseCase.execute(command);
    }

    /** {@inheritDoc} */
    @Override
    public Order cancel(Long orderId) {
        return cancelOrderUseCase.execute(orderId);
    }

    /** {@inheritDoc} */
    @Override
    public Order markAsPaid(Long orderId) {
        return markOrderAsPaidUseCase.execute(orderId);
    }

    /** {@inheritDoc} */
    @Override
    public Order revertToPending(Long orderId) {
        return revertOrderToPendingUseCase.execute(orderId);
    }
}
