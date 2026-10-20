package com.shoppingcart.auth.application.query.port.output;

import java.util.Optional;

import com.shoppingcart.auth.domain.entity.User;

/**
 * Output port for loading an existing {@link User} from the persistence layer (query side).
 *
 * <p>Implemented by {@link com.shoppingcart.auth.framework.output.persistence.adapters.UserPersistenceAdapter}.
 * Returns {@link Optional} values so callers decide whether to throw or silently handle the
 * absence of a user, following the convention used across this codebase.</p>
 */
public interface LoadUserPort {

    /**
     * Looks up a user by their unique e-mail address.
     *
     * @param email the e-mail address to search for
     * @return an {@link Optional} containing the matching user, or empty if not found
     */
    Optional<User> findByEmail(String email);

    /**
     * Looks up a user by their database identifier.
     *
     * @param id the database-assigned user ID
     * @return an {@link Optional} containing the matching user, or empty if not found
     */
    Optional<User> findById(Long id);
}
