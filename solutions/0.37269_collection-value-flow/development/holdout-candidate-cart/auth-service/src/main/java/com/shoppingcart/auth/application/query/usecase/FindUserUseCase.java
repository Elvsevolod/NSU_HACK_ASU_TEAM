package com.shoppingcart.auth.application.query.usecase;

import com.shoppingcart.auth.application.query.port.output.LoadUserPort;
import com.shoppingcart.auth.domain.entity.User;
import com.shoppingcart.auth.domain.exception.UserNotFoundException;

/**
 * Use case that retrieves an existing user by e-mail address.
 *
 * <p>Delegates to {@link LoadUserPort} and converts an empty result into a
 * {@link UserNotFoundException}, providing a consistent error contract to all callers.</p>
 */
public class FindUserUseCase {

    private final LoadUserPort loadUserPort;

    /**
     * @param loadUserPort output port for loading a user from the persistence layer
     */
    public FindUserUseCase(LoadUserPort loadUserPort) {
        this.loadUserPort = loadUserPort;
    }

    /**
     * Returns the user with the given e-mail address.
     *
     * @param email the e-mail address to look up
     * @return the matching {@link User}
     * @throws UserNotFoundException if no user is found with the supplied e-mail
     */
    public User findByEmail(String email) {
        return loadUserPort.findByEmail(email)
                .orElseThrow(() -> new UserNotFoundException(email));
    }
}
