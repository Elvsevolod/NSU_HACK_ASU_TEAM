package com.shoppingcart.auth.framework.output.mapper;

import com.shoppingcart.auth.domain.entity.User;
import com.shoppingcart.auth.framework.output.persistence.entity.UserJpaEntity;

/**
 * Stateless mapper that converts between {@link User} domain objects and
 * {@link UserJpaEntity} JPA entities.
 *
 * <p>All methods are static; this class is not meant to be instantiated. It isolates
 * all persistence-mapping concerns from both the domain layer and the adapter class.</p>
 */
public class UserPersistenceMapper {

    private UserPersistenceMapper() {}

    /**
     * Converts a domain {@link User} aggregate into a JPA entity ready for persistence.
     *
     * @param user the domain user to convert
     * @return a fully populated {@link UserJpaEntity}
     */
    public static UserJpaEntity toJpa(User user) {
        UserJpaEntity entity = new UserJpaEntity();
        entity.setId(user.getId());
        entity.setEmail(user.getEmail());
        entity.setPassword(user.getPassword());
        entity.setRole(user.getRole());
        return entity;
    }

    /**
     * Reconstitutes a domain {@link User} aggregate from a JPA entity loaded from the database.
     *
     * <p>Uses the reconstitution constructor {@link User#User(Long, String, String, com.shoppingcart.auth.domain.vo.Role)},
     * which wraps the password via {@link com.shoppingcart.auth.domain.vo.Password#ofHash(String)}
     * and skips plain-text length validation.</p>
     *
     * @param entity the JPA entity to convert
     * @return a fully hydrated {@link User} domain object
     */
    public static User toDomain(UserJpaEntity entity) {
        return new User(entity.getId(), entity.getEmail(), entity.getPassword(), entity.getRole());
    }
}
