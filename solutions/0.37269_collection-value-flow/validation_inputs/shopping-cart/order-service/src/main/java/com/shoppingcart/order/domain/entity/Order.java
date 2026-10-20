package com.shoppingcart.order.domain.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import com.shoppingcart.order.domain.exceptions.OrderAlreadyCancelledException;
import com.shoppingcart.order.domain.vo.OrderId;
import com.shoppingcart.order.domain.vo.OrderStatus;

/**
 * Aggregate root representing a customer order in the shopping cart domain.
 *
 * <p>
 * An {@code Order} is the central entity of this bounded context. It owns a
 * list of
 * {@link OrderDetail} line items and enforces all business invariants around
 * lifecycle
 * transitions (pending → confirmed → paid / cancelled). Construction is
 * restricted to
 * two static factory methods to guarantee that every instance starts in a valid
 * state.
 * </p>
 *
 * <p>
 * The details list is defensively copied on construction and exposed as an
 * unmodifiable
 * view to preserve encapsulation.
 * </p>
 */
public class Order {

    private final OrderId id;
    private final Customer customer;
    private final List<OrderDetail> details;
    private OrderStatus status;
    private final LocalDateTime createdAt;

    private Order(OrderId id, Customer customer,
            List<OrderDetail> details, OrderStatus status,
            LocalDateTime createdAt) {
        this.id = id;
        this.customer = customer;
        this.details = new ArrayList<>(details);
        this.status = status;
        this.createdAt = createdAt;
    }

    /**
     * Creates a brand-new order with {@link OrderStatus#PENDING} status and no
     * persisted ID.
     *
     * @param customer the customer placing the order
     * @param details  one or more line items; must not be {@code null} or empty
     * @return a new {@code Order} instance ready to be persisted
     * @throws IllegalArgumentException if {@code details} is {@code null} or empty
     */
    public static Order create(Customer customer, List<OrderDetail> details) {
        if (details == null || details.isEmpty())
            throw new IllegalArgumentException("Order must have at least one detail");
        return new Order(new OrderId(null), customer, details, OrderStatus.PENDING, LocalDateTime.now());
    }

    /**
     * Reconstitutes an {@code Order} from its persisted state (e.g., loaded from
     * the database).
     *
     * @param id        the persisted numeric identifier
     * @param customer  the associated customer
     * @param details   the line items belonging to the order
     * @param status    the current lifecycle status
     * @param createdAt the timestamp when the order was originally created
     * @return a fully hydrated {@code Order} reflecting the stored state
     */
    public static Order reconstitute(Long id, Customer customer,
            List<OrderDetail> details, OrderStatus status, LocalDateTime createdAt) {
        return new Order(new OrderId(id), customer, details, status, createdAt);
    }

    /**
     * Transitions the order from {@link OrderStatus#PENDING} to
     * {@link OrderStatus#CONFIRMED}.
     *
     * @throws IllegalStateException if the order is not currently in
     *                               {@code PENDING} status
     */
    public void confirm() {
        if (this.status != OrderStatus.PENDING)
            throw new IllegalStateException("Only PENDING orders can be confirmed");
        this.status = OrderStatus.CONFIRMED;
    }

    /**
     * Cancels the order, transitioning it to {@link OrderStatus#CANCELLED}.
     *
     * @throws OrderAlreadyCancelledException if the order is already cancelled
     * @throws IllegalStateException          if the order has already been paid
     */
    public void cancel() {
        if (this.status == OrderStatus.CANCELLED)
            throw new OrderAlreadyCancelledException(this.id);
        if (this.status == OrderStatus.PAID)
            throw new IllegalStateException("A paid order cannot be cancelled");
        this.status = OrderStatus.CANCELLED;
    }

    /**
     * Marks the order as paid, transitioning it to {@link OrderStatus#PAID}.
     *
     * @throws IllegalStateException if the order is not in {@code PENDING} or
     *                               {@code CONFIRMED} status
     */
    public void markAsPaid() {
        if (this.status != OrderStatus.PENDING && this.status != OrderStatus.CONFIRMED)
            throw new IllegalStateException("Only PENDING or CONFIRMED orders can be marked as paid");
        this.status = OrderStatus.PAID;
    }

    /**
     * Reverts a paid order back to {@link OrderStatus#PENDING}, typically after a
     * payment rollback.
     *
     * @throws IllegalStateException if the order is not currently in {@code PAID}
     *                               status
     */
    public void revertToPending() {
        if (this.status != OrderStatus.PAID)
            throw new IllegalStateException("Only PAID orders can be reverted to pending");
        this.status = OrderStatus.PENDING;
    }

    /**
     * Calculates the total monetary amount of the order by summing each detail's
     * subtotal.
     *
     * @return the sum of all {@link OrderDetail#subtotal()} values, never
     *         {@code null}
     */
    public BigDecimal total() {
        return details.stream()
                .map(OrderDetail::subtotal)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    /**
     * @return the order identifier, which may have a {@code null} value if not yet
     *         persisted
     */
    public OrderId getId() {
        return id;
    }

    /** @return the customer who placed the order */
    public Customer getCustomer() {
        return customer;
    }

    /** @return an unmodifiable view of the order's line items */
    public List<OrderDetail> getDetails() {
        return Collections.unmodifiableList(details);
    }

    /** @return the current lifecycle status of the order */
    public OrderStatus getStatus() {
        return status;
    }

    /** @return the timestamp when the order was created */
    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
}
