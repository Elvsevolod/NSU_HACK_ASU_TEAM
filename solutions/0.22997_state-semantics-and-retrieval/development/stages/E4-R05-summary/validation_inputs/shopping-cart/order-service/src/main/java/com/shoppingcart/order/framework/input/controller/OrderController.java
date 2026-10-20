package com.shoppingcart.order.framework.input.controller;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.shoppingcart.order.application.command.port.input.CancelOrder;
import com.shoppingcart.order.application.command.port.input.CreateOrder;
import com.shoppingcart.order.application.command.port.input.MarkOrderAsPaid;
import com.shoppingcart.order.application.command.port.input.RevertOrderToPending;
import com.shoppingcart.order.application.query.port.input.GetOrder;
import com.shoppingcart.order.application.query.port.input.ListOrdersByCustomer;
import com.shoppingcart.order.framework.input.dto.CreateOrderRequest;
import com.shoppingcart.order.framework.input.dto.OrderResponse;
import com.shoppingcart.order.framework.input.mapper.OrderHttpMapper;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;

/**
 * REST controller that exposes the order management API under {@code /api/orders}.
 *
 * <p>Acts as the primary input adapter in the hexagonal architecture: it translates
 * incoming HTTP requests into application port calls and maps the resulting domain objects
 * back to HTTP responses via {@link OrderHttpMapper}. It depends exclusively on input port
 * interfaces, never on concrete service or use-case classes.</p>
 */
@Tag(name = "Orders", description = "Order management")
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final CreateOrder createOrder;
    private final CancelOrder cancelOrder;
    private final MarkOrderAsPaid markOrderAsPaid;
    private final RevertOrderToPending revertOrderToPending;
    private final GetOrder getOrder;
    private final ListOrdersByCustomer listOrdersByCustomer;

    /**
     * @param createOrder           port for creating a new order
     * @param cancelOrder           port for cancelling an order
     * @param markOrderAsPaid       port for marking an order as paid
     * @param revertOrderToPending  port for reverting a paid order back to pending
     * @param getOrder              port for retrieving a single order by ID
     * @param listOrdersByCustomer  port for listing all orders of a customer
     */
    public OrderController(CreateOrder createOrder, CancelOrder cancelOrder,
            MarkOrderAsPaid markOrderAsPaid, RevertOrderToPending revertOrderToPending,
            GetOrder getOrder, ListOrdersByCustomer listOrdersByCustomer) {
        this.createOrder = createOrder;
        this.cancelOrder = cancelOrder;
        this.markOrderAsPaid = markOrderAsPaid;
        this.revertOrderToPending = revertOrderToPending;
        this.getOrder = getOrder;
        this.listOrdersByCustomer = listOrdersByCustomer;
    }

    /**
     * Creates a new order from the validated request body.
     *
     * @param request the incoming order creation request
     * @return 201 Created with the persisted order as {@link OrderResponse}
     */
    @Operation(summary = "Create a new order")
    @ApiResponse(responseCode = "201", description = "Order created successfully")
    @PostMapping
    public ResponseEntity<OrderResponse> create(@Valid @RequestBody CreateOrderRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(OrderHttpMapper.toResponse(createOrder.create(OrderHttpMapper.toCommand(request))));
    }

    /**
     * Cancels the order with the given ID.
     *
     * @param id the numeric identifier of the order to cancel
     * @return 200 OK with the updated order, or 404 if not found
     */
    @Operation(summary = "Cancel an order")
    @ApiResponse(responseCode = "200", description = "Order cancelled")
    @ApiResponse(responseCode = "404", description = "Order not found")
    @PatchMapping("/{id}/cancel")
    public ResponseEntity<OrderResponse> cancel(@PathVariable Long id) {
        return ResponseEntity.ok(OrderHttpMapper.toResponse(cancelOrder.cancel(id)));
    }

    /**
     * Marks the order with the given ID as paid.
     *
     * @param id the numeric identifier of the order to mark as paid
     * @return 200 OK with the updated order, or 404 if not found
     */
    @Operation(summary = "Mark an order as paid")
    @ApiResponse(responseCode = "200", description = "Order marked as paid")
    @ApiResponse(responseCode = "404", description = "Order not found")
    @PatchMapping("/{id}/pay")
    public ResponseEntity<OrderResponse> pay(@PathVariable Long id) {
        return ResponseEntity.ok(OrderHttpMapper.toResponse(markOrderAsPaid.markAsPaid(id)));
    }

    /**
     * Reverts the payment of the order with the given ID, returning it to {@code PENDING} status.
     *
     * @param id the numeric identifier of the order to revert
     * @return 200 OK with the updated order, or 404 if not found
     */
    @Operation(summary = "Revert an order payment back to pending")
    @ApiResponse(responseCode = "200", description = "Order reverted to pending")
    @ApiResponse(responseCode = "404", description = "Order not found")
    @PatchMapping("/{id}/revert-payment")
    public ResponseEntity<OrderResponse> revertPayment(@PathVariable Long id) {
        return ResponseEntity.ok(OrderHttpMapper.toResponse(revertOrderToPending.revertToPending(id)));
    }

    /**
     * Retrieves the order with the given ID.
     *
     * @param id the numeric identifier of the order to retrieve
     * @return 200 OK with the order, or 404 if not found
     */
    @Operation(summary = "Get order by ID")
    @ApiResponse(responseCode = "200", description = "Order found")
    @ApiResponse(responseCode = "404", description = "Order not found")
    @GetMapping("/{id}")
    public ResponseEntity<OrderResponse> getById(@PathVariable Long id) {
        return ResponseEntity.ok(OrderHttpMapper.toResponse(getOrder.getById(id)));
    }

    /**
     * Returns all orders belonging to the specified customer.
     *
     * @param customerId the identifier of the customer whose orders are to be listed
     * @return 200 OK with a (possibly empty) list of orders
     */
    @Operation(summary = "List orders by customer")
    @ApiResponse(responseCode = "200", description = "List of orders")
    @GetMapping
    public ResponseEntity<List<OrderResponse>> listByCustomer(@RequestParam Long customerId) {
        return ResponseEntity.ok(listOrdersByCustomer.listByCustomer(customerId)
                .stream().map(OrderHttpMapper::toResponse).toList());
    }
}
