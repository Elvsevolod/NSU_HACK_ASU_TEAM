package com.shoppingcart.order.framework.output.client.adapters;

import java.util.Optional;

import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import com.shoppingcart.order.application.command.port.output.ProductValidationPort;
import com.shoppingcart.order.domain.exceptions.InvalidProductException;
import com.shoppingcart.order.framework.output.client.dto.ProductClientDto;

/**
 * Output adapter that implements {@link ProductValidationPort} by calling the external
 * product service over HTTP.
 *
 * <p>Translates HTTP responses from the product service into domain-compatible values,
 * isolating the rest of the application from the remote API's DTO structure
 * ({@link ProductClientDto}). Network errors are wrapped in an unchecked
 * {@link RuntimeException} to propagate them as infrastructure failures.</p>
 */
public class ProductClientAdapter implements ProductValidationPort {

    private final RestTemplate restTemplate;
    private final String productServiceUrl;

    /**
     * @param restTemplate     the HTTP client used to call the product service
     * @param productServiceUrl the base URL of the product service (e.g., {@code http://product-service/api/products})
     */
    public ProductClientAdapter(RestTemplate restTemplate, String productServiceUrl) {
        this.restTemplate = restTemplate;
        this.productServiceUrl = productServiceUrl;
    }

    /**
     * Fetches a product from the product service by its ID.
     *
     * @param productId the identifier of the product to fetch
     * @return an {@link Optional} containing the product data if found, or empty if the service returns null
     * @throws RuntimeException if the HTTP call fails
     */
    public Optional<ProductClientDto> getProductById(Long productId) {
        try {
            String url = productServiceUrl + "/" + productId;
            ProductClientDto product = restTemplate.getForObject(url, ProductClientDto.class);
            return Optional.ofNullable(product);
        } catch (HttpClientErrorException.NotFound e) {
            return Optional.empty();
        }
    }

    /**
     * {@inheritDoc}
     *
     * @throws InvalidProductException if the product does not exist in the product service
     */
    public Double getProductPrice(Long productId) {
        return getProductById(productId)
                .map(ProductClientDto::price)
                .orElseThrow(() -> new InvalidProductException(productId));
    }
}
