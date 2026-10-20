package com.shoppingcart.auth.framework.output.persistence.adapters;

import java.util.Optional;

import com.shoppingcart.auth.application.command.port.output.SaveUserPort;
import com.shoppingcart.auth.application.query.port.output.LoadUserPort;
import com.shoppingcart.auth.domain.entity.User;
import com.shoppingcart.auth.framework.output.mapper.UserPersistenceMapper;
import com.shoppingcart.auth.framework.output.persistence.repository.UserJpaRepository;

/**
 * Persistence adapter that implements both the write-side and read-side user repository ports.
 *
 * <p>Bridges the application layer with the JPA infrastructure by delegating all database
 * operations to {@link UserJpaRepository} and using {@link UserPersistenceMapper} to translate
 * between domain objects and JPA entities.</p>
 *
 * <p>Implements:</p>
 * <ul>
 *   <li>{@link SaveUserPort} — write-side port (save)</li>
 *   <li>{@link LoadUserPort} — read-side port (findByEmail, findById)</li>
 * </ul>
 */
public class UserPersistenceAdapter implements SaveUserPort, LoadUserPort {

    private final UserJpaRepository jpaRepository;

    /**
     * @param jpaRepository the Spring Data JPA repository used for all database operations
     */
    public UserPersistenceAdapter(UserJpaRepository jpaRepository) {
        this.jpaRepository = jpaRepository;
    }

    /** {@inheritDoc} */
    @Override
    public User save(User user) {
        return UserPersistenceMapper.toDomain(
                jpaRepository.save(UserPersistenceMapper.toJpa(user)));
    }

    /** {@inheritDoc} */
    @Override
    public Optional<User> findByEmail(String email) {
        return jpaRepository.findByEmail(email)
                .map(UserPersistenceMapper::toDomain);
    }

    /** {@inheritDoc} */
    @Override
    public Optional<User> findById(Long id) {
        return jpaRepository.findById(id)
                .map(UserPersistenceMapper::toDomain);
    }
}
