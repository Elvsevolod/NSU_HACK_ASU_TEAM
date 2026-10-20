package com.shoppingcart.payment.framework.output.client.adapters;

import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import com.shoppingcart.payment.application.command.port.output.OrderStatusPort;
import com.shoppingcart.payment.application.command.port.output.OrderValidationPort;
import com.shoppingcart.payment.domain.exceptions.OrderNotFoundException;
import com.shoppingcart.payment.domain.exceptions.OrderNotValidForPaymentException;
import com.shoppingcart.payment.framework.output.client.dto.OrderClientDto;

/**
 * Output adapter that communicates with the order-service over HTTP, implementing both
 * {@link OrderValidationPort} and {@link OrderStatusPort}.
 *
 * <p>A single adapter implements both ports because both operations target the same
 * downstream service. It translates HTTP responses and error codes into domain exceptions,
 * isolating the rest of the application from the order-service's REST API details.</p>
 */
public class OrderClientAdapter implements OrderValidationPort, OrderStatusPort {

    private final RestTemplate restTemplate;
    private final String orderServiceUrl;

    /**
     * @param restTemplate    the HTTP client used to call the order-service
     * @param orderServiceUrl the base URL of the order-service (e.g., {@code http://localhost:8083/api/orders})
     */
    public OrderClientAdapter(RestTemplate restTemplate, String orderServiceUrl) {
        this.restTemplate = restTemplate;
        this.orderServiceUrl = orderServiceUrl;
    }

    /**
     * {@inheritDoc}
     *
     * @throws OrderNotFoundException          if the order-service returns 404 or a null body
     * @throws OrderNotValidForPaymentException if the order status is {@code CANCELLED} or {@code PAID}
     */
    @Override
    public OrderClientDto getOrderIfValid(Long orderId) {
        try {
            OrderClientDto order = restTemplate.getForObject(orderServiceUrl + "/" + orderId, OrderClientDto.class);
            if (order == null)
                throw new OrderNotFoundException(orderId);
            if ("CANCELLED".equals(order.status()) || "PAID".equals(order.status()))
                throw new OrderNotValidForPaymentException(orderId, order.status());
            return order;
        } catch (HttpClientErrorException.NotFound e) {
            throw new OrderNotFoundException(orderId);
        }
    }

    /**
     * {@inheritDoc}
     *
     * <p>Calls {@code PATCH /api/orders/{orderId}/pay} on the order-service.</p>
     */
    @Override
    public void markAsPaid(Long orderId) {
        restTemplate.patchForObject(orderServiceUrl + "/" + orderId + "/pay", null, Void.class);
    }

    /**
     * {@inheritDoc}
     *
     * <p>Calls {@code PATCH /api/orders/{orderId}/revert-payment} on the order-service.</p>
     */
    @Override
    public void revertToPending(Long orderId) {
        restTemplate.patchForObject(orderServiceUrl + "/" + orderId + "/revert-payment", null, Void.class);
    }
}
