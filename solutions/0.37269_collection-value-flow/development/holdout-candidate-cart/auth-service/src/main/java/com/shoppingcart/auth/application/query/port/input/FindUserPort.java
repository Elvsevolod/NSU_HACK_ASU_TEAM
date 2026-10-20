package com.shoppingcart.auth.application.query.port.input;

import java.util.Optional;

import com.shoppingcart.auth.domain.entity.User;

/**
 * Input port for the user query use case (query side).
 *
 * <p>Implemented by {@link com.shoppingcart.auth.application.query.service.UserQueryService}
 * and consumed by components that need to look up a user by e-mail without triggering a
 * command (e.g. security filters or other services).</p>
 */
public interface FindUserPort {

    /**
     * Finds a user by their e-mail address.
     *
     * @param email the e-mail address to search for
     * @return an {@link Optional} containing the user if found, or empty if not found
     */
    Optional<User> findByEmail(String email);
}