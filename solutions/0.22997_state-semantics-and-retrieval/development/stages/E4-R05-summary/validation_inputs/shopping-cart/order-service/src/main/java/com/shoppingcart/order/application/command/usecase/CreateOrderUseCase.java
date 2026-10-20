package com.shoppingcart.order.application.command.usecase;

import java.math.BigDecimal;
import java.util.List;

import com.shoppingcart.order.application.command.dto.CreateOrderCommand;
import com.shoppingcart.order.application.command.dto.CreateOrderCommand.OrderDetailCommand;
import com.shoppingcart.order.application.command.port.output.OrderCommandRepository;
import com.shoppingcart.order.application.command.port.output.ProductValidationPort;
import com.shoppingcart.order.domain.entity.Customer;
import com.shoppingcart.order.domain.entity.Order;
import com.shoppingcart.order.domain.entity.OrderDetail;
import com.shoppingcart.order.domain.exceptions.PriceMismatchException;
import com.shoppingcart.order.domain.vo.Quantity;

/**
 * Use case responsible for placing a new order.
 *
 * <p>Orchestrates the following steps:</p>
 * <ol>
 *   <li>Reconstitutes the {@link Customer} from command data.</li>
 *   <li>For each line item, fetches the authoritative price from the product catalog via
 *       {@link ProductValidationPort} and rejects the command if the client-supplied price
 *       does not match.</li>
 *   <li>Builds the list of {@link OrderDetail} domain objects.</li>
 *   <li>Creates the {@link Order} aggregate (starts in {@code PENDING} status) and persists it.</li>
 * </ol>
 */
public class CreateOrderUseCase {

    private final OrderCommandRepository orderCommandRepository;
    private final ProductValidationPort productValidationPort;

    /**
     * @param orderCommandRepository the persistence port used to save the new order
     * @param productValidationPort  the external port used to validate product prices
     */
    public CreateOrderUseCase(OrderCommandRepository orderCommandRepository,
            ProductValidationPort productValidationPort) {
        this.orderCommandRepository = orderCommandRepository;
        this.productValidationPort = productValidationPort;
    }

    /**
     * Executes the create-order use case.
     *
     * @param command the command containing customer and line-item data
     * @return the newly created and persisted {@link Order}
     * @throws PriceMismatchException   if a line item's price does not match the catalog price
     * @throws com.shoppingcart.order.domain.exceptions.InvalidProductException if a product is unavailable
     * @throws IllegalArgumentException if the command contains no line items
     */
    public Order execute(CreateOrderCommand command) {
        Customer customer = toCustomer(command);
        List<OrderDetail> details = toOrderDetails(command.details());
        return orderCommandRepository.save(Order.create(customer, details));
    }

    /**
     * Reconstitutes a {@link Customer} domain object from the incoming command.
     *
     * @param command the command carrying the customer's ID, name, and e-mail
     * @return a fully hydrated {@link Customer} ready to be attached to the order
     */
    private Customer toCustomer(CreateOrderCommand command) {
        return Customer.reconstitute(
                command.customerId(),
                command.customerName(),
                command.customerEmail());
    }

    /**
     * Validates each line item's price and converts it to an {@link OrderDetail} domain object.
     *
     * @param detailCommands the raw line-item commands from the incoming request
     * @return an immutable list of validated {@link OrderDetail} instances
     */
    private List<OrderDetail> toOrderDetails(List<OrderDetailCommand> detailCommands) {
        return detailCommands.stream()
                .map(d -> {
                    validatePrice(d);
                    return toOrderDetail(d);
                })
                .toList();
    }

    /**
     * Checks that the client-supplied unit price matches the authoritative catalog price.
     *
     * @param d the line-item command to validate
     * @throws PriceMismatchException if the prices differ
     */
    private void validatePrice(OrderDetailCommand d) {
        Double actualPrice = productValidationPort.getProductPrice(d.productId());
        if (Double.compare(actualPrice, d.unitPrice()) != 0)
            throw new PriceMismatchException(d.productId(), d.unitPrice(), actualPrice);
    }

    /**
     * Maps a raw line-item command to an {@link OrderDetail} domain object.
     *
     * @param d the line-item command to map
     * @return a new {@link OrderDetail} ready to be added to the order
     */
    private OrderDetail toOrderDetail(OrderDetailCommand d) {
        return OrderDetail.create(
                d.productId(),
                d.productName(),
                new Quantity(d.quantity()),
                BigDecimal.valueOf(d.unitPrice()));
    }

}
