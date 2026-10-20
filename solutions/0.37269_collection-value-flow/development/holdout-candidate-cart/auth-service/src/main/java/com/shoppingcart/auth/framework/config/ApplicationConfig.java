package com.shoppingcart.auth.framework.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.shoppingcart.auth.application.command.port.output.PasswordEncoderPort;
import com.shoppingcart.auth.application.command.port.output.SaveUserPort;
import com.shoppingcart.auth.application.command.port.output.TokenGeneratorPort;
import com.shoppingcart.auth.application.command.usecase.LoginUserUseCase;
import com.shoppingcart.auth.application.command.usecase.RegisterUserUseCase;
import com.shoppingcart.auth.application.query.port.output.LoadUserPort;
import com.shoppingcart.auth.application.query.usecase.FindUserUseCase;
import com.shoppingcart.auth.framework.output.persistence.adapters.UserPersistenceAdapter;
import com.shoppingcart.auth.framework.output.persistence.repository.UserJpaRepository;

/**
 * Composition root for the auth-service.
 *
 * <p>Wires all use cases and the persistence adapter as Spring beans, keeping both the use
 * cases and the adapter free of {@code @Component} or {@code @Service} annotations. Port
 * interfaces resolved by Spring match the implementations registered here:</p>
 * <ul>
 *   <li>{@link SaveUserPort} and {@link LoadUserPort} → {@link UserPersistenceAdapter}</li>
 *   <li>{@link PasswordEncoderPort} → {@link com.shoppingcart.auth.framework.config.PasswordEncoderAdapter}</li>
 *   <li>{@link TokenGeneratorPort} → {@link com.shoppingcart.auth.framework.config.JwtService}</li>
 * </ul>
 */
@Configuration
public class ApplicationConfig {

    /**
     * Creates the {@link RegisterUserUseCase} bean with all required output ports.
     *
     * @param saveUserPort    port for persisting the new user
     * @param loadUserPort    port for duplicate e-mail detection
     * @param passwordEncoder port for BCrypt hashing
     * @param tokenGenerator  port for issuing JWTs after registration
     * @return the configured use case instance
     */
    @Bean
    public RegisterUserUseCase registerUserUseCase(SaveUserPort saveUserPort,
            LoadUserPort loadUserPort, PasswordEncoderPort passwordEncoder,
            TokenGeneratorPort tokenGenerator) {
        return new RegisterUserUseCase(saveUserPort, loadUserPort, passwordEncoder, tokenGenerator);
    }

    /**
     * Creates the {@link LoginUserUseCase} bean with all required output ports.
     *
     * @param loadUserPort    port for looking up the user by e-mail
     * @param passwordEncoder port for verifying BCrypt hashes
     * @param tokenGenerator  port for issuing JWTs after successful login
     * @return the configured use case instance
     */
    @Bean
    public LoginUserUseCase loginUserUseCase(LoadUserPort loadUserPort,
            PasswordEncoderPort passwordEncoder, TokenGeneratorPort tokenGenerator) {
        return new LoginUserUseCase(loadUserPort, passwordEncoder, tokenGenerator);
    }

    /**
     * Creates the {@link FindUserUseCase} bean used by the query service.
     *
     * @param loadUserPort port for loading a user by e-mail or ID
     * @return the configured use case instance
     */
    @Bean
    public FindUserUseCase findUserUseCase(LoadUserPort loadUserPort) {
        return new FindUserUseCase(loadUserPort);
    }

    /**
     * Creates the {@link UserPersistenceAdapter} bean, which satisfies both
     * {@link SaveUserPort} and {@link LoadUserPort}.
     *
     * @param jpaRepository Spring Data JPA repository for user entities
     * @return the configured persistence adapter
     */
    @Bean
    public UserPersistenceAdapter userPersistenceAdapter(UserJpaRepository jpaRepository) {
        return new UserPersistenceAdapter(jpaRepository);
    }
}
