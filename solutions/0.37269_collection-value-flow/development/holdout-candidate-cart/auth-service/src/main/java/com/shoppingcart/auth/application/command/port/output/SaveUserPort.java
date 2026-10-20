package com.shoppingcart.auth.application.command.port.output;

import com.shoppingcart.auth.domain.entity.User;

/**
 * Output port for persisting a {@link User} aggregate.
 *
 * <p>Implemented by {@link com.shoppingcart.auth.framework.output.persistence.adapters.UserPersistenceAdapter}.
 * Returns the saved entity with the database-assigned identifier populated.</p>
 */
public interface SaveUserPort {

    /**
     * Persists the given user and returns the saved instance with a populated ID.
     *
     * @param user the user to persist
     * @return the saved user with the database-assigned identifier
     */
    User save(User user);
}
