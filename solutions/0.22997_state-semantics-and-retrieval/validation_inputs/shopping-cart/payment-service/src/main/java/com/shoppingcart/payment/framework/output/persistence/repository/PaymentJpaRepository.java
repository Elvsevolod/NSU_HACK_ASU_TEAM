package com.shoppingcart.payment.framework.output.persistence.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.shoppingcart.payment.domain.vo.PaymentStatus;
import com.shoppingcart.payment.framework.output.persistence.entity.PaymentJpaEntity;

/**
 * Spring Data JPA repository for {@link PaymentJpaEntity}.
 *
 * <p>Extends {@link JpaRepository} to inherit standard CRUD operations. Both custom
 * derived queries are resolved automatically by Spring Data from their method names,
 * requiring no explicit JPQL.</p>
 */
public interface PaymentJpaRepository extends JpaRepository<PaymentJpaEntity, Long> {

    /**
     * Returns all payment entities associated with the given order ID.
     *
     * @param orderId the identifier of the order
     * @return a (possibly empty) list of payments for the order
     */
    List<PaymentJpaEntity> findByOrderId(Long orderId);

    /**
     * Checks whether any payment for the given order exists with one of the specified statuses.
     * Used to prevent duplicate active payments for the same order.
     *
     * @param orderId  the identifier of the order to check
     * @param statuses the list of statuses considered "active" (typically {@code PENDING} and {@code APPROVED})
     * @return {@code true} if a matching payment exists, {@code false} otherwise
     */
    boolean existsByOrderIdAndStatusIn(Long orderId, List<PaymentStatus> statuses);
}
