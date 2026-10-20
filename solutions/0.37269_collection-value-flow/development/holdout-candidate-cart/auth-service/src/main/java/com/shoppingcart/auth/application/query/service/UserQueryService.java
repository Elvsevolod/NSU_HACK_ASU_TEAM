package com.shoppingcart.auth.application.query.service;

import java.util.Optional;

import org.springframework.stereotype.Service;

import com.shoppingcart.auth.application.query.port.input.FindUserPort;
import com.shoppingcart.auth.application.query.usecase.FindUserUseCase;
import com.shoppingcart.auth.domain.entity.User;

/**
 * Spring-managed service that exposes the query-side user lookup as an input port.
 *
 * <p>Implements {@link FindUserPort} and delegates to {@link FindUserUseCase}, keeping the use
 * case free of Spring annotations. The result is always wrapped in {@link Optional#of} because
 * {@link FindUserUseCase#findByEmail(String)} throws {@link com.shoppingcart.auth.domain.exception.UserNotFoundException}
 * rather than returning empty.</p>
 */
@Service
public class UserQueryService implements FindUserPort {

    private final FindUserUseCase findUserUseCase;

    /**
     * @param findUserUseCase use case that loads and returns a user or throws if not found
     */
    public UserQueryService(FindUserUseCase findUserUseCase) {
        this.findUserUseCase = findUserUseCase;
    }

    /** {@inheritDoc} */
    @Override
    public Optional<User> findByEmail(String email) {
        return Optional.of(findUserUseCase.findByEmail(email));
    }
}
