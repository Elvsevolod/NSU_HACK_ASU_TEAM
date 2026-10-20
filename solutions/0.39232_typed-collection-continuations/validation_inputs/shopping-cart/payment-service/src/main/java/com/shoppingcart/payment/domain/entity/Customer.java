package com.shoppingcart.payment.domain.entity;

/**
 * Read-only snapshot of a customer within the payment bounded context.
 *
 * <p>This entity is not managed or persisted by the payment service. It exists solely to
 * carry customer identification data that may be included in payment-related DTOs or
 * order validation responses. Instances are immutable once created.</p>
 */
public class Customer {

    private final Long id;
    private final String name;
    private final String email;

    private Customer(Long id, String name, String email) {
        this.id = id;
        this.name = name;
        this.email = email;
    }

    /**
     * Reconstitutes a {@code Customer} from external data (e.g., order-service response).
     *
     * @param id    the customer's unique identifier
     * @param name  the customer's full name
     * @param email the customer's e-mail address
     * @return a fully populated {@code Customer} instance
     */
    public static Customer reconstitute(Long id, String name, String email) {
        return new Customer(id, name, email);
    }

    /** @return the customer's unique identifier */
    public Long getId() { return id; }

    /** @return the customer's full name */
    public String getName() { return name; }

    /** @return the customer's e-mail address */
    public String getEmail() { return email; }
}
