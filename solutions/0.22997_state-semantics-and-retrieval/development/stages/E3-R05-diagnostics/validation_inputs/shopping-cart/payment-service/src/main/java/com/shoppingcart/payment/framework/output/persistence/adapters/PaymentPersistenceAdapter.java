package com.shoppingcart.payment.framework.output.persistence.adapters;

import java.util.List;

import com.shoppingcart.payment.application.command.port.output.PaymentCommandRepository;
import com.shoppingcart.payment.application.query.port.output.PaymentQueryRepository;
import com.shoppingcart.payment.domain.entity.Payment;
import com.shoppingcart.payment.domain.exceptions.PaymentNotFoundException;
import com.shoppingcart.payment.domain.vo.PaymentStatus;
import com.shoppingcart.payment.framework.output.mapper.PaymentPersistenceMapper;
import com.shoppingcart.payment.framework.output.persistence.repository.PaymentJpaRepository;

/**
 * Persistence adapter that implements both the command and query repository output ports.
 *
 * <p>Bridges the application layer with the JPA infrastructure by delegating all database
 * operations to {@link PaymentJpaRepository} and using {@link PaymentPersistenceMapper}
 * to translate between domain objects and JPA entities.</p>
 *
 * <p>Implements:</p>
 * <ul>
 *   <li>{@link PaymentCommandRepository} — write-side port (save, findById, existsActivePaymentForOrder)</li>
 *   <li>{@link PaymentQueryRepository} — read-side port (findById, findByOrderId)</li>
 * </ul>
 */
public class PaymentPersistenceAdapter implements PaymentCommandRepository, PaymentQueryRepository {

    private final PaymentJpaRepository jpaRepository;

    /**
     * @param jpaRepository the Spring Data JPA repository used for all database operations
     */
    public PaymentPersistenceAdapter(PaymentJpaRepository jpaRepository) {
        this.jpaRepository = jpaRepository;
    }

    /** {@inheritDoc} */
    @Override
    public Payment save(Payment payment) {
        return PaymentPersistenceMapper.toDomain(
                jpaRepository.save(PaymentPersistenceMapper.toJpa(payment)));
    }

    /** {@inheritDoc} */
    @Override
    public Payment findById(Long id) {
        return jpaRepository.findById(id)
                .map(PaymentPersistenceMapper::toDomain)
                .orElseThrow(() -> new PaymentNotFoundException(id));
    }

    /** {@inheritDoc} */
    @Override
    public boolean existsActivePaymentForOrder(Long orderId) {
        return jpaRepository.existsByOrderIdAndStatusIn(orderId,
                List.of(PaymentStatus.PENDING, PaymentStatus.APPROVED));
    }

    /** {@inheritDoc} */
    @Override
    public List<Payment> findByOrderId(Long orderId) {
        return jpaRepository.findByOrderId(orderId)
                .stream()
                .map(PaymentPersistenceMapper::toDomain)
                .toList();
    }
}
