package com.shoppingcart.auth.application.command.usecase;

import com.shoppingcart.auth.application.command.dto.LoginCommand;
import com.shoppingcart.auth.application.command.port.output.PasswordEncoderPort;
import com.shoppingcart.auth.application.command.port.output.TokenGeneratorPort;
import com.shoppingcart.auth.application.query.port.output.LoadUserPort;
import com.shoppingcart.auth.domain.entity.User;
import com.shoppingcart.auth.domain.exception.InvalidPasswordException;
import com.shoppingcart.auth.domain.exception.UserNotFoundException;

/**
 * Use case that authenticates an existing user and issues a JWT.
 *
 * <p>Execution steps:</p>
 * <ol>
 *   <li>Look up the user by e-mail via {@link LoadUserPort}; throw {@link UserNotFoundException} if absent.</li>
 *   <li>Verify the plain-text password against the stored BCrypt hash via {@link PasswordEncoderPort}.</li>
 *   <li>Generate and return a signed JWT via {@link TokenGeneratorPort}.</li>
 * </ol>
 */
public class LoginUserUseCase {

    private final LoadUserPort loadUserPort;
    private final PasswordEncoderPort passwordEncoder;
    private final TokenGeneratorPort tokenGenerator;

    /**
     * @param loadUserPort    output port for loading a user from the persistence layer
     * @param passwordEncoder output port for verifying BCrypt password hashes
     * @param tokenGenerator  output port for issuing signed JWTs
     */
    public LoginUserUseCase(LoadUserPort loadUserPort, PasswordEncoderPort passwordEncoder,
            TokenGeneratorPort tokenGenerator) {
        this.loadUserPort = loadUserPort;
        this.passwordEncoder = passwordEncoder;
        this.tokenGenerator = tokenGenerator;
    }

    /**
     * Authenticates the user identified by the command and returns a JWT.
     *
     * @param command the login credentials
     * @return a signed JWT token for the authenticated user
     * @throws UserNotFoundException    if no user exists with the supplied e-mail
     * @throws InvalidPasswordException if the supplied password does not match the stored hash
     */
    public String execute(LoginCommand command) {
        User user = loadUserPort.findByEmail(command.email())
                .orElseThrow(() -> new UserNotFoundException(command.email()));

        if (!passwordEncoder.matches(command.password(), user.getPassword()))
            throw new InvalidPasswordException("Invalid credentials");

        return tokenGenerator.generateToken(user.getEmail());
    }
}
