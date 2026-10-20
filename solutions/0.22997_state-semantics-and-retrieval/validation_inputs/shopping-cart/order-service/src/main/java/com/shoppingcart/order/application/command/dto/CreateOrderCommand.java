package com.shoppingcart.order.application.command.dto;

import java.util.List;

/**
 * Immutable command object carrying all the data required to create a new order.
 *
 * <p>This record is produced by the input adapter (e.g., REST controller) and consumed
 * by {@link com.shoppingcart.order.application.command.port.input.CreateOrder}. It crosses
 * the boundary between the framework and the application layer, decoupling the HTTP request
 * model from the domain.</p>
 *
 * @param customerId    the unique identifier of the customer placing the order
 * @param customerName  the full name of the customer at the time of order placement
 * @param customerEmail the e-mail address of the customer at the time of order placement
 * @param details       one or more line items describing the products being ordered
 */
public record CreateOrderCommand(
    Long customerId,
    String customerName,
    String customerEmail,
    List<OrderDetailCommand> details
) {

    /**
     * Nested command object representing a single product line item within the order.
     *
     * @param productId   the identifier of the product in the catalog
     * @param productName the product name as displayed to the customer
     * @param quantity    the number of units requested; must be greater than zero
     * @param unitPrice   the price per unit as supplied by the client; validated against the catalog
     */
    public record OrderDetailCommand(
        Long productId,
        String productName,
        int quantity,
        double unitPrice
    ) {}
}
