package com.shoppingcart.payment.application.command.port.output;

/**
 * Output port for updating order status in the order-service after a payment event.
 *
 * <p>The application layer uses this port to notify the order-service of payment outcomes
 * without depending on the HTTP client implementation. The framework layer provides the
 * concrete adapter ({@link com.shoppingcart.payment.framework.output.client.adapters.OrderClientAdapter}).</p>
 */
public interface OrderStatusPort {

    /**
     * Notifies the order-service to transition the order to {@code PAID} status.
     *
     * @param orderId the identifier of the order to mark as paid
     */
    void markAsPaid(Long orderId);

    /**
     * Notifies the order-service to revert the order from {@code PAID} back to {@code PENDING}.
     * Called after a successful refund.
     *
     * @param orderId the identifier of the order to revert
     */
    void revertToPending(Long orderId);
}
