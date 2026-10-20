package com.shoppingcart.payment.framework.output.mapper;

import com.shoppingcart.payment.domain.entity.Payment;
import com.shoppingcart.payment.framework.output.persistence.entity.PaymentJpaEntity;

/**
 * Stateless mapper that converts between domain {@link Payment} objects and
 * {@link PaymentJpaEntity} JPA entities.
 *
 * <p>All methods are static; this class is not meant to be instantiated. It isolates
 * all persistence-mapping concerns from both the domain layer and the adapter class.</p>
 */
public class PaymentPersistenceMapper {

    private PaymentPersistenceMapper() {}

    /**
     * Converts a domain {@link Payment} aggregate into a JPA entity ready for persistence.
     *
     * @param payment the domain payment to convert
     * @return a fully populated {@link PaymentJpaEntity}
     */
    public static PaymentJpaEntity toJpa(Payment payment) {
        PaymentJpaEntity entity = new PaymentJpaEntity();
        entity.setId(payment.getId());
        entity.setOrderId(payment.getOrderId());
        entity.setCustomerId(payment.getCustomerId());
        entity.setAmount(payment.getAmount());
        entity.setPaymentMethod(payment.getPaymentMethod());
        entity.setStatus(payment.getStatus());
        entity.setCreatedAt(payment.getCreatedAt());
        return entity;
    }

    /**
     * Reconstitutes a domain {@link Payment} aggregate from a JPA entity loaded from the database.
     *
     * @param entity the JPA entity to convert
     * @return a fully hydrated {@link Payment} domain object
     */
    public static Payment toDomain(PaymentJpaEntity entity) {
        return Payment.reconstitute(
                entity.getId(),
                entity.getOrderId(),
                entity.getCustomerId(),
                entity.getAmount(),
                entity.getPaymentMethod(),
                entity.getStatus(),
                entity.getCreatedAt());
    }
}
