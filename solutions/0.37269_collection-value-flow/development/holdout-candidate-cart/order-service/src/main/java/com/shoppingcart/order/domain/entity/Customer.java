package com.shoppingcart.order.domain.entity;

/**
 * Domain entity representing the customer associated with an {@link Order}.
 *
 * <p>
 * {@code Customer} is a value-like entity within the order bounded context: it
 * carries
 * enough identifying information (ID, name, e-mail) to describe who placed the
 * order without
 * coupling this service to a full user-management domain. Instances are
 * immutable once created.
 * </p>
 *
 * <p>
 * Construction is performed exclusively through the
 * {@link #reconstitute(Long, String, String)}
 * factory method, which enforces that {@code name} and {@code email} are always
 * non-blank.
 * </p>
 */
public class Customer {

    private final Long id;
    private final String name;
    private final String email;

    private Customer(Long id, String name, String email) {
        if (name == null || name.isBlank())
            throw new IllegalArgumentException("Customer name cannot be blank");
        if (email == null || email.isBlank())
            throw new IllegalArgumentException("Customer email cannot be blank");
        this.id = id;
        this.name = name;
        this.email = email;
    }

    /**
     * Reconstitutes a {@code Customer} from its persisted representation.
     *
     * @param id    the customer's unique identifier in the user service
     * @param name  the customer's full name; must not be blank
     * @param email the customer's e-mail address; must not be blank
     * @return a fully hydrated {@code Customer} instance
     * @throws IllegalArgumentException if {@code name} or {@code email} is blank
     */
    public static Customer reconstitute(Long id, String name, String email) {
        return new Customer(id, name, email);
    }

    /** @return the customer's unique identifier */
    public Long getId() {
        return id;
    }

    /** @return the customer's full name */
    public String getName() {
        return name;
    }

    /** @return the customer's e-mail address */
    public String getEmail() {
        return email;
    }
}
