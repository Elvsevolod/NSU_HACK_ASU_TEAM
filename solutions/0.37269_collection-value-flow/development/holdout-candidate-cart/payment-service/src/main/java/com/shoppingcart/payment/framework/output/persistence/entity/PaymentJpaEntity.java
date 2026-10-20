package com.shoppingcart.payment.framework.output.persistence.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import com.shoppingcart.payment.domain.vo.PaymentMethod;
import com.shoppingcart.payment.domain.vo.PaymentStatus;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * JPA entity mapped to the {@code payments} table.
 *
 * <p>Represents the persisted state of a payment. Both {@link com.shoppingcart.payment.domain.vo.PaymentStatus}
 * and {@link com.shoppingcart.payment.domain.vo.PaymentMethod} are stored as strings
 * ({@link EnumType#STRING}) to keep the schema readable and resilient to enum reordering.</p>
 */
@Getter
@Setter
@NoArgsConstructor
@Entity
@Table(name = "payments")
public class PaymentJpaEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(nullable = false)
    private Long orderId;
    @Column(nullable = false)
    private Long customerId;
    @Column(nullable = false)
    private BigDecimal amount;
    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private PaymentMethod paymentMethod;
    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private PaymentStatus status;
    @Column(nullable = false)
    private LocalDateTime createdAt;
}
