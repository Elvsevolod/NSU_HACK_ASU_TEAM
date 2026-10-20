package com.shoppingcart.auth.framework.output.persistence.entity;

import com.shoppingcart.auth.domain.vo.Role;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * JPA entity mapped to the {@code users} table.
 *
 * <p>Represents the persisted state of a user account. The {@link Role} enum is stored as a
 * string ({@link EnumType#STRING}) to keep the schema readable and resilient to enum reordering.
 * The {@code email} column carries a unique constraint enforced at both the database level and
 * the application layer via {@link com.shoppingcart.auth.application.command.usecase.RegisterUserUseCase}.</p>
 */
@Getter
@Setter
@NoArgsConstructor
@Entity
@Table(name = "users")
public class UserJpaEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String email;

    @Column(nullable = false)
    private String password;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Role role;
}
