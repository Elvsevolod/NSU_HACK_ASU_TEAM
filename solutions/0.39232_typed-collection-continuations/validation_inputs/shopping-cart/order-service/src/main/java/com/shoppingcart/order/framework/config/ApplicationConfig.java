package com.shoppingcart.order.framework.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

import com.shoppingcart.order.application.command.port.output.OrderCommandRepository;
import com.shoppingcart.order.application.command.service.OrderCommandService;
import com.shoppingcart.order.application.query.port.output.OrderQueryRepository;
import com.shoppingcart.order.application.query.service.OrderQueryService;
import com.shoppingcart.order.framework.output.client.adapters.ProductClientAdapter;

/**
 * Spring configuration class responsible for wiring the application's beans.
 *
 * <p>Acts as the composition root for the hexagonal architecture: it instantiates and
 * connects the output adapters (persistence, HTTP client) with the application services,
 * keeping all infrastructure wiring out of the domain and application layers.</p>
 */
@Configuration
public class ApplicationConfig {

    /** Base URL of the external product service, injected from {@code application.properties}. */
    @Value("${product.service.url}")
    private String productServiceUrl;

    /**
     * Provides a shared {@link RestTemplate} used for outgoing HTTP calls.
     *
     * @return a default {@link RestTemplate} instance
     */
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }

    /**
     * Creates the {@link ProductClientAdapter} that implements {@link com.shoppingcart.order.application.command.port.output.ProductValidationPort}.
     *
     * @param restTemplate the HTTP client used to call the product service
     * @return a configured {@link ProductClientAdapter}
     */
    @Bean
    public ProductClientAdapter productClientAdapter(RestTemplate restTemplate) {
        return new ProductClientAdapter(restTemplate, productServiceUrl);
    }

    /**
     * Creates the command-side application service, wiring it with its required output ports.
     *
     * @param orderCommandRepository the persistence adapter implementing {@link com.shoppingcart.order.application.command.port.output.OrderCommandRepository}
     * @param productClientAdapter   the HTTP adapter implementing {@link com.shoppingcart.order.application.command.port.output.ProductValidationPort}
     * @return a fully wired {@link OrderCommandService}
     */
    @Bean
    public OrderCommandService orderCommandService(OrderCommandRepository orderCommandRepository,
            ProductClientAdapter productClientAdapter) {
        return new OrderCommandService(orderCommandRepository, productClientAdapter);
    }

    /**
     * Creates the query-side application service, wiring it with its required output port.
     *
     * @param orderQueryRepository the persistence adapter implementing {@link com.shoppingcart.order.application.query.port.output.OrderQueryRepository}
     * @return a fully wired {@link OrderQueryService}
     */
    @Bean
    public OrderQueryService orderQueryService(OrderQueryRepository orderQueryRepository) {
        return new OrderQueryService(orderQueryRepository);
    }
}
