package com.shoppingcart.order.application.query.service;

import java.util.List;

import com.shoppingcart.order.application.query.port.input.GetOrder;
import com.shoppingcart.order.application.query.port.input.ListOrdersByCustomer;
import com.shoppingcart.order.application.query.port.output.OrderQueryRepository;
import com.shoppingcart.order.application.query.usecase.GetOrderUseCase;
import com.shoppingcart.order.application.query.usecase.ListOrdersByCustomerUseCase;
import com.shoppingcart.order.domain.entity.Order;

/**
 * Application service that fulfills all read-side (query) input ports.
 *
 * <p>Acts as the single entry point for all order-reading operations. Delegates each
 * query to a dedicated use-case class, keeping concerns focused and independently testable.</p>
 *
 * <p>Implements the following input ports:</p>
 * <ul>
 *   <li>{@link GetOrder}</li>
 *   <li>{@link ListOrdersByCustomer}</li>
 * </ul>
 */
public class OrderQueryService implements GetOrder, ListOrdersByCustomer {

    private final GetOrderUseCase getOrderUseCase;
    private final ListOrdersByCustomerUseCase listOrdersByCustomerUseCase;

    /**
     * Constructs the service and wires each use case with the required repository port.
     *
     * @param orderQueryRepository the read-only persistence port for loading orders
     */
    public OrderQueryService(OrderQueryRepository orderQueryRepository) {
        this.getOrderUseCase = new GetOrderUseCase(orderQueryRepository);
        this.listOrdersByCustomerUseCase = new ListOrdersByCustomerUseCase(orderQueryRepository);
    }

    /** {@inheritDoc} */
    @Override
    public Order getById(Long orderId) {
        return getOrderUseCase.execute(orderId);
    }

    /** {@inheritDoc} */
    @Override
    public List<Order> listByCustomer(Long customerId) {
        return listOrdersByCustomerUseCase.execute(customerId);
    }

}
