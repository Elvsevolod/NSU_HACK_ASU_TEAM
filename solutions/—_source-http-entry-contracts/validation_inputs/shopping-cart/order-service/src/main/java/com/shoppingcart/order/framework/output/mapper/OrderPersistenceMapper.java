package com.shoppingcart.order.framework.output.mapper;

import java.util.List;

import com.shoppingcart.order.domain.entity.Customer;
import com.shoppingcart.order.domain.entity.Order;
import com.shoppingcart.order.domain.entity.OrderDetail;
import com.shoppingcart.order.domain.vo.Quantity;
import com.shoppingcart.order.framework.output.persistence.entity.OrderDetailJpaEntity;
import com.shoppingcart.order.framework.output.persistence.entity.OrderJpaEntity;

/**
 * Stateless mapper that converts between domain objects and JPA entities.
 *
 * <p>All methods are static; this class is not meant to be instantiated. It isolates
 * all persistence-mapping concerns from both the domain layer and the adapter class
 * ({@link com.shoppingcart.order.framework.output.persistence.adapters.OrderPersistenceAdapter}),
 * keeping each class focused on a single responsibility.</p>
 */
public class OrderPersistenceMapper {

    private OrderPersistenceMapper() {}

    /**
     * Converts a domain {@link Order} aggregate into a JPA entity ready for persistence.
     *
     * @param order the domain order to convert
     * @return a fully populated {@link OrderJpaEntity} including its detail children
     */
    public static OrderJpaEntity toJpa(Order order) {
        OrderJpaEntity entity = new OrderJpaEntity();
        entity.setId(order.getId().value());
        entity.setCustomerId(order.getCustomer().getId());
        entity.setCustomerName(order.getCustomer().getName());
        entity.setCustomerEmail(order.getCustomer().getEmail());
        entity.setStatus(order.getStatus());
        entity.setCreatedAt(order.getCreatedAt());

        List<OrderDetailJpaEntity> details = order.getDetails().stream()
                .map(d -> toDetailJpa(d, entity))
                .toList();
        entity.setDetails(details);

        return entity;
    }

    /**
     * Reconstitutes a domain {@link Order} aggregate from a JPA entity loaded from the database.
     *
     * @param entity the JPA entity to convert
     * @return a fully hydrated {@link Order} domain aggregate
     */
    public static Order toDomain(OrderJpaEntity entity) {
        Customer customer = Customer.reconstitute(
                entity.getCustomerId(),
                entity.getCustomerName(),
                entity.getCustomerEmail());

        List<OrderDetail> details = entity.getDetails().stream()
                .map(OrderPersistenceMapper::toDetailDomain)
                .toList();

        return Order.reconstitute(
                entity.getId(),
                customer,
                details,
                entity.getStatus(),
                entity.getCreatedAt());
    }

    /**
     * Converts a single domain {@link OrderDetail} line item into its JPA entity representation.
     *
     * @param detail the domain line item to convert
     * @param order  the parent {@link OrderJpaEntity} to associate this detail with
     * @return a populated {@link OrderDetailJpaEntity}
     */
    private static OrderDetailJpaEntity toDetailJpa(OrderDetail detail, OrderJpaEntity order) {
        OrderDetailJpaEntity entity = new OrderDetailJpaEntity();
        entity.setId(detail.getId());
        entity.setOrder(order);
        entity.setProductId(detail.getProductId());
        entity.setProductName(detail.getProductName());
        entity.setQuantity(detail.getQuantity().value());
        entity.setUnitPrice(detail.getUnitPrice());
        return entity;
    }

    /**
     * Reconstitutes a domain {@link OrderDetail} line item from its JPA entity.
     *
     * @param entity the JPA line-item entity to convert
     * @return a fully hydrated {@link OrderDetail} domain object
     */
    private static OrderDetail toDetailDomain(OrderDetailJpaEntity entity) {
        return OrderDetail.reconstitute(
                entity.getId(),
                entity.getProductId(),
                entity.getProductName(),
                new Quantity(entity.getQuantity()),
                entity.getUnitPrice());
    }
}
