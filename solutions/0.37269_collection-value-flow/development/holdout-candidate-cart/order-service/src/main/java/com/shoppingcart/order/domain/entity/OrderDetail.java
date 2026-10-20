package com.shoppingcart.order.domain.entity;

import java.math.BigDecimal;

import com.shoppingcart.order.domain.vo.Quantity;

/**
 * Domain entity representing a single line item within an {@link Order}.
 *
 * <p>
 * An {@code OrderDetail} captures a snapshot of a product at the time the order
 * was placed,
 * storing the product ID, name, quantity, and unit price. This snapshot
 * approach ensures that
 * historical order data remains consistent even if the product catalog changes
 * later.
 * </p>
 *
 * <p>
 * Instances are immutable. Two static factory methods control creation:
 * </p>
 * <ul>
 * <li>{@link #create} — for new line items not yet persisted (no DB ID)</li>
 * <li>{@link #reconstitute} — for rehydrating line items from the database</li>
 * </ul>
 */
public class OrderDetail {

    private final Long id;
    private final Long productId;
    private final String productName;
    private final Quantity quantity;
    private final BigDecimal unitPrice;

    private OrderDetail(Long id, Long productId, String productName,
            Quantity quantity, BigDecimal unitPrice) {
        if (productId == null)
            throw new IllegalArgumentException("Product id cannot be null");
        if (unitPrice == null || unitPrice.compareTo(BigDecimal.ZERO) < 0)
            throw new IllegalArgumentException("Unit price cannot be negative");
        this.id = id;
        this.productId = productId;
        this.productName = productName;
        this.quantity = quantity;
        this.unitPrice = unitPrice;
    }

    /**
     * Creates a new, unpersisted line item for an order being placed.
     *
     * @param productId   the identifier of the product in the product catalog
     * @param productName the product name at the time of the order
     * @param quantity    the number of units ordered; must be greater than zero
     * @param unitPrice   the price per unit at the time of the order; must not be
     *                    negative
     * @return a new {@code OrderDetail} with no persisted ID
     * @throws IllegalArgumentException if {@code productId} is {@code null} or
     *                                  {@code unitPrice} is negative
     */
    public static OrderDetail create(Long productId, String productName,
            Quantity quantity, BigDecimal unitPrice) {
        return new OrderDetail(null, productId, productName, quantity, unitPrice);
    }

    /**
     * Reconstitutes an {@code OrderDetail} from its persisted state (e.g., loaded
     * from the database).
     *
     * @param id          the persisted numeric identifier of this line item
     * @param productId   the identifier of the product
     * @param productName the product name snapshot
     * @param quantity    the number of units
     * @param unitPrice   the price per unit
     * @return a fully hydrated {@code OrderDetail} reflecting the stored state
     */
    public static OrderDetail reconstitute(Long id, Long productId, String productName,
            Quantity quantity, BigDecimal unitPrice) {
        return new OrderDetail(id, productId, productName, quantity, unitPrice);
    }

    /**
     * Calculates the subtotal for this line item ({@code unitPrice × quantity}).
     *
     * @return the monetary subtotal, never {@code null}
     */
    public BigDecimal subtotal() {
        return unitPrice.multiply(BigDecimal.valueOf(quantity.value()));
    }

    /**
     * @return the persisted identifier of this line item, or {@code null} if not
     *         yet saved
     */
    public Long getId() {
        return id;
    }

    /** @return the product identifier referencing the product catalog */
    public Long getProductId() {
        return productId;
    }

    /** @return the snapshot of the product name at order creation time */
    public String getProductName() {
        return productName;
    }

    /** @return the quantity of units ordered */
    public Quantity getQuantity() {
        return quantity;
    }

    /** @return the unit price recorded at the time of the order */
    public BigDecimal getUnitPrice() {
        return unitPrice;
    }
}
