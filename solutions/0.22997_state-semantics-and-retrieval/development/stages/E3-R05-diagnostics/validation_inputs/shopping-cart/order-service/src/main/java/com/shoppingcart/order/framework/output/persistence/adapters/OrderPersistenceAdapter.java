package com.shoppingcart.order.framework.output.persistence.adapters;

import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Component;

import com.shoppingcart.order.application.command.port.output.OrderCommandRepository;
import com.shoppingcart.order.application.query.port.output.OrderQueryRepository;
import com.shoppingcart.order.domain.entity.Order;
import com.shoppingcart.order.domain.vo.OrderId;
import com.shoppingcart.order.framework.output.mapper.OrderPersistenceMapper;
import com.shoppingcart.order.framework.output.persistence.entity.OrderJpaEntity;
import com.shoppingcart.order.framework.output.persistence.repository.OrderJpaRepository;

/**
 * Persistence adapter that implements both the command and query repository output ports.
 *
 * <p>Bridges the application layer with the JPA infrastructure by delegating all database
 * operations to {@link OrderJpaRepository} and using {@link OrderPersistenceMapper} to
 * translate between domain objects and JPA entities. A single adapter handles both read
 * and write sides because they share the same underlying data store.</p>
 *
 * <p>Implements:</p>
 * <ul>
 *   <li>{@link OrderCommandRepository} — write-side port (save, findById for commands)</li>
 *   <li>{@link OrderQueryRepository} — read-side port (findById, findByCustomerId)</li>
 * </ul>
 */
@Component
public class OrderPersistenceAdapter implements OrderCommandRepository, OrderQueryRepository {

    private final OrderJpaRepository orderJpaRepository;

    /**
     * @param orderJpaRepository the Spring Data JPA repository used for all database operations
     */
    public OrderPersistenceAdapter(OrderJpaRepository orderJpaRepository) {
        this.orderJpaRepository = orderJpaRepository;
    }

    /** {@inheritDoc} */
    @Override
    public Optional<Order> findById(OrderId id) {
        return orderJpaRepository.findById(id.value())
                .map(OrderPersistenceMapper::toDomain);
    }

    /** {@inheritDoc} */
    @Override
    public Order save(Order order) {
        OrderJpaEntity saved = orderJpaRepository.save(OrderPersistenceMapper.toJpa(order));
        return OrderPersistenceMapper.toDomain(saved);
    }

    /** {@inheritDoc} */
    @Override
    public List<Order> findByCustomerId(Long customerId) {
        return orderJpaRepository.findByCustomerId(customerId).stream()
                .map(OrderPersistenceMapper::toDomain)
                .toList();
    }
}
