package com.shoppingcart.order.framework.input.dto;

import java.util.List;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

/**
 * Incoming HTTP request body for the create-order endpoint ({@code POST /api/orders}).
 *
 * <p>All fields are validated with Bean Validation annotations before the controller
 * forwards the request to the application layer. Validation errors are collected and
 * returned as a structured 400 response by {@link com.shoppingcart.order.framework.exceptions.GlobalExceptionHandler}.</p>
 *
 * @param customerId    the unique identifier of the customer placing the order
 * @param customerName  the full name of the customer; must not be blank
 * @param customerEmail a valid e-mail address for the customer
 * @param details       one or more product line items; must not be empty
 */
public record CreateOrderRequest(

        @NotNull(message = "Customer id is required")
        Long customerId,

        @NotBlank(message = "Customer name is required")
        String customerName,

        @NotBlank(message = "Customer email is required")
        @Email(message = "Customer email is not valid")
        String customerEmail,

        @NotEmpty(message = "Order must have at least one detail")
        @Valid
        List<OrderDetailRequest> details

) {
    /**
     * Nested request object representing a single product line item within the order.
     *
     * @param productId   the identifier of the product in the catalog; must not be null
     * @param productName the display name of the product; must not be blank
     * @param quantity    the number of units to order; must be greater than zero
     * @param unitPrice   the price per unit as supplied by the client; must be greater than zero
     */
    public record OrderDetailRequest(

            @NotNull(message = "Product id is required")
            @Positive(message = "Product id must be a positive number")
            Long productId,

            @NotBlank(message = "Product name is required")
            String productName,

            @Positive(message = "Quantity must be greater than zero")
            int quantity,

            @Positive(message = "Unit price must be greater than zero")
            double unitPrice
    ) {}
}
