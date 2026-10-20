package com.shoppingcart.auth.framework.output.persistence.repository;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.shoppingcart.auth.framework.output.persistence.entity.UserJpaEntity;

/**
 * Spring Data JPA repository for {@link UserJpaEntity}.
 *
 * <p>Extends {@link JpaRepository} to inherit standard CRUD operations. The custom derived
 * query {@link #findByEmail(String)} is resolved automatically by Spring Data from the method
 * name, requiring no explicit JPQL.</p>
 */
public interface UserJpaRepository extends JpaRepository<UserJpaEntity, Long> {

    /**
     * Returns the user entity whose e-mail matches the given value.
     *
     * <p>Because the {@code email} column is declared unique, at most one result is returned.</p>
     *
     * @param email the e-mail address to search for
     * @return an {@link Optional} containing the matching entity, or empty if not found
     */
    Optional<UserJpaEntity> findByEmail(String email);
}
