package com.shoppingcart.order.framework.output.persistence.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.shoppingcart.order.framework.output.persistence.entity.OrderJpaEntity;

/**
 * Spring Data JPA repository for {@link OrderJpaEntity}.
 *
 * <p>Extends {@link JpaRepository} to inherit standard CRUD operations. The custom
 * derived query {@link #findByCustomerId} is resolved automatically by Spring Data
 * from the method name, requiring no explicit JPQL.</p>
 */
public interface OrderJpaRepository extends JpaRepository<OrderJpaEntity, Long> {

    /**
     * Returns all order entities associated with the given customer ID.
     *
     * @param customerId the identifier of the customer
     * @return a (possibly empty) list of {@link OrderJpaEntity} belonging to the customer
     */
    List<OrderJpaEntity> findByCustomerId(Long customerId);
}
