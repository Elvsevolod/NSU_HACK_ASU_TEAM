package com.shoppingcart.payment.domain.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import com.shoppingcart.payment.domain.exceptions.InvalidPaymentAmountException;
import com.shoppingcart.payment.domain.exceptions.PaymentAlreadyProcessedException;
import com.shoppingcart.payment.domain.vo.PaymentMethod;
import com.shoppingcart.payment.domain.vo.PaymentStatus;

/**
 * Aggregate root representing a payment attempt for an order.
 *
 * <p>A {@code Payment} starts in {@link PaymentStatus#PENDING} and transitions to
 * {@code APPROVED}, {@code REJECTED}, or {@code REFUNDED} through explicit domain methods.
 * All state transitions enforce invariants: only a {@code PENDING} payment can be approved
 * or rejected, and only an {@code APPROVED} payment can be refunded.</p>
 *
 * <p>Construction is restricted to two static factory methods:</p>
 * <ul>
 *   <li>{@link #create} — for new payments not yet persisted</li>
 *   <li>{@link #reconstitute} — for rehydrating payments from the database</li>
 * </ul>
 */
public class Payment {
    private Long id;
    private Long orderId;
    private Long customerId;
    private BigDecimal amount;
    private PaymentMethod paymentMethod;
    private PaymentStatus status;
    private LocalDateTime createdAt;

    private Payment(Long id, Long orderId, Long customerId, BigDecimal amount, PaymentMethod paymentMethod,
            PaymentStatus status, LocalDateTime createdAt) {
        this.id = id;
        this.orderId = orderId;
        this.customerId = customerId;
        this.amount = amount;
        this.paymentMethod = paymentMethod;
        this.status = status;
        this.createdAt = createdAt;
    }

    /**
     * Creates a new, unpersisted payment in {@link PaymentStatus#PENDING} status.
     *
     * @param orderId       the identifier of the order being paid
     * @param customerId    the identifier of the customer making the payment
     * @param amount        the payment amount; must be greater than zero
     * @param paymentMethod the method used for the payment
     * @return a new {@code Payment} ready to be approved, rejected, and persisted
     * @throws InvalidPaymentAmountException if {@code amount} is null, zero, or negative
     */
    public static Payment create(Long orderId, Long customerId, BigDecimal amount, PaymentMethod paymentMethod) {
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0)
            throw new InvalidPaymentAmountException();
        return new Payment(null, orderId, customerId, amount, paymentMethod, PaymentStatus.PENDING,
                LocalDateTime.now());
    }

    /**
     * Reconstitutes a {@code Payment} from its persisted state (e.g., loaded from the database).
     *
     * @param id            the persisted numeric identifier
     * @param orderId       the associated order identifier
     * @param customerId    the associated customer identifier
     * @param amount        the payment amount
     * @param method        the payment method used
     * @param status        the current lifecycle status
     * @param createdAt     the timestamp when the payment was originally created
     * @return a fully hydrated {@code Payment} reflecting the stored state
     */
    public static Payment reconstitute(Long id, Long orderId, Long customerId,
            BigDecimal amount, PaymentMethod method, PaymentStatus status, LocalDateTime createdAt) {
        return new Payment(id, orderId, customerId, amount, method, status, createdAt);
    }

    /**
     * Transitions the payment to {@link PaymentStatus#APPROVED}.
     *
     * @return this payment instance for fluent chaining
     * @throws PaymentAlreadyProcessedException if the payment is not in {@code PENDING} status
     */
    public Payment approve() {
        if (this.status != PaymentStatus.PENDING)
            throw new PaymentAlreadyProcessedException(this.id);
        this.status = PaymentStatus.APPROVED;
        return this;
    }

    /**
     * Transitions the payment to {@link PaymentStatus#REJECTED}.
     *
     * @return this payment instance for fluent chaining
     * @throws PaymentAlreadyProcessedException if the payment is not in {@code PENDING} status
     */
    public Payment reject() {
        if (this.status != PaymentStatus.PENDING)
            throw new PaymentAlreadyProcessedException(this.id);
        this.status = PaymentStatus.REJECTED;
        return this;
    }

    /**
     * Transitions the payment to {@link PaymentStatus#REFUNDED}.
     *
     * @return this payment instance for fluent chaining
     * @throws PaymentAlreadyProcessedException if the payment is not in {@code APPROVED} status
     */
    public Payment refund() {
        if (this.status != PaymentStatus.APPROVED)
            throw new PaymentAlreadyProcessedException(this.id);
        this.status = PaymentStatus.REFUNDED;
        return this;
    }

    /** @return the persisted identifier, or {@code null} if not yet saved */
    public Long getId() { return id; }

    /** @return the identifier of the order this payment belongs to */
    public Long getOrderId() { return orderId; }

    /** @return the identifier of the customer who initiated the payment */
    public Long getCustomerId() { return customerId; }

    /** @return the monetary amount of this payment */
    public BigDecimal getAmount() { return amount; }

    /** @return the payment method used */
    public PaymentMethod getPaymentMethod() { return paymentMethod; }

    /** @return the current lifecycle status of the payment */
    public PaymentStatus getStatus() { return status; }

    /** @return the timestamp when the payment was created */
    public LocalDateTime getCreatedAt() { return createdAt; }

}
