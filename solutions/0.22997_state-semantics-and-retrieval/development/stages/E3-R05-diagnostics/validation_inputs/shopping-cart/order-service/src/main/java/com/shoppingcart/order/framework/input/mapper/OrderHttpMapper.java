package com.shoppingcart.order.framework.input.mapper;

import com.shoppingcart.order.application.command.dto.CreateOrderCommand;
import com.shoppingcart.order.domain.entity.Order;
import com.shoppingcart.order.framework.input.dto.CreateOrderRequest;
import com.shoppingcart.order.framework.input.dto.OrderResponse;
import com.shoppingcart.order.framework.input.dto.OrderResponse.OrderDetailResponse;

/**
 * Stateless mapper that converts between HTTP-layer DTOs and application-layer objects.
 *
 * <p>All methods are static; this class is not meant to be instantiated. It isolates
 * the mapping logic from the controller, keeping each class focused on a single
 * responsibility.</p>
 */
public class OrderHttpMapper {

    private OrderHttpMapper() {}

    /**
     * Converts an HTTP request body into an application-layer command.
     *
     * @param request the validated incoming HTTP request
     * @return a {@link CreateOrderCommand} ready to be passed to the input port
     */
    public static CreateOrderCommand toCommand(CreateOrderRequest request) {
        return new CreateOrderCommand(
                request.customerId(),
                request.customerName(),
                request.customerEmail(),
                request.details().stream()
                        .map(d -> new CreateOrderCommand.OrderDetailCommand(
                                d.productId(),
                                d.productName(),
                                d.quantity(),
                                d.unitPrice()))
                        .toList());
    }

    /**
     * Converts a domain {@link Order} aggregate into an HTTP response body.
     *
     * @param order the domain order to serialize
     * @return an {@link OrderResponse} suitable for JSON serialization
     */
    public static OrderResponse toResponse(Order order) {
        return new OrderResponse(
                order.getId().value(),
                order.getCustomer().getId(),
                order.getCustomer().getName(),
                order.getCustomer().getEmail(),
                order.getStatus().name(),
                order.getCreatedAt(),
                order.total(),
                order.getDetails().stream()
                        .map(d -> new OrderDetailResponse(
                                d.getId(),
                                d.getProductId(),
                                d.getProductName(),
                                d.getQuantity().value(),
                                d.getUnitPrice(),
                                d.subtotal()))
                        .toList());
    }
}
