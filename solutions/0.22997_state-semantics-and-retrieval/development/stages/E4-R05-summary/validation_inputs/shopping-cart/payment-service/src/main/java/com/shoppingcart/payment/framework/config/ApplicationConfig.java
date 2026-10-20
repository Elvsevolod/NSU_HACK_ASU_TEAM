package com.shoppingcart.payment.framework.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.HttpComponentsClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

import com.shoppingcart.payment.application.command.service.PaymentCommandService;
import com.shoppingcart.payment.application.query.service.PaymentQueryService;
import com.shoppingcart.payment.framework.output.client.adapters.OrderClientAdapter;
import com.shoppingcart.payment.framework.output.persistence.adapters.PaymentPersistenceAdapter;
import com.shoppingcart.payment.framework.output.persistence.repository.PaymentJpaRepository;

/**
 * Spring configuration class responsible for wiring the payment service beans.
 *
 * <p>Acts as the composition root: it instantiates and connects the output adapters
 * (persistence, HTTP client to order-service) with the application services, keeping
 * all infrastructure wiring out of the domain and application layers.</p>
 */
@Configuration
public class ApplicationConfig {

    /** Base URL of the order-service, injected from {@code application.properties}. */
    @Value("${order.service.url}")
    private String orderServiceUrl;

    /**
     * Provides a shared {@link RestTemplate} used for outgoing HTTP calls to the order-service.
     *
     * @return a default {@link RestTemplate} instance
     */
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate(new HttpComponentsClientHttpRequestFactory());
    }

    /**
     * Creates the {@link OrderClientAdapter}, which implements both
     * {@link com.shoppingcart.payment.application.command.port.output.OrderValidationPort} and
     * {@link com.shoppingcart.payment.application.command.port.output.OrderStatusPort}.
     *
     * @param restTemplate the HTTP client used to call the order-service
     * @return a configured {@link OrderClientAdapter}
     */
    @Bean
    public OrderClientAdapter orderClientAdapter(RestTemplate restTemplate) {
        return new OrderClientAdapter(restTemplate, orderServiceUrl);
    }

    /**
     * Creates the persistence adapter that implements both command and query repository ports.
     *
     * @param jpaRepository the Spring Data JPA repository for payment entities
     * @return a configured {@link PaymentPersistenceAdapter}
     */
    @Bean
    public PaymentPersistenceAdapter paymentPersistenceAdapter(PaymentJpaRepository jpaRepository) {
        return new PaymentPersistenceAdapter(jpaRepository);
    }

    /**
     * Creates the command-side application service, wiring it with persistence and order-service ports.
     *
     * @param adapter            the persistence adapter (used as {@code PaymentCommandRepository})
     * @param orderClientAdapter the HTTP adapter (used as both validation and status ports)
     * @return a fully wired {@link PaymentCommandService}
     */
    @Bean
    public PaymentCommandService paymentCommandService(PaymentPersistenceAdapter adapter,
            OrderClientAdapter orderClientAdapter) {
        return new PaymentCommandService(adapter, orderClientAdapter, orderClientAdapter);
    }

    /**
     * Creates the query-side application service.
     *
     * @param adapter the persistence adapter (used as {@code PaymentQueryRepository})
     * @return a fully wired {@link PaymentQueryService}
     */
    @Bean
    public PaymentQueryService paymentQueryService(PaymentPersistenceAdapter adapter) {
        return new PaymentQueryService(adapter);
    }
}
