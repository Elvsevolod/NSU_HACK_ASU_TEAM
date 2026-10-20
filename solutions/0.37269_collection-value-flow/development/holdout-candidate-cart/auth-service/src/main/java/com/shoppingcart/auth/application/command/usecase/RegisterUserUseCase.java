package com.shoppingcart.auth.application.command.usecase;

import com.shoppingcart.auth.application.command.dto.RegisterCommand;
import com.shoppingcart.auth.application.command.port.output.PasswordEncoderPort;
import com.shoppingcart.auth.application.command.port.output.SaveUserPort;
import com.shoppingcart.auth.application.command.port.output.TokenGeneratorPort;
import com.shoppingcart.auth.application.query.port.output.LoadUserPort;
import com.shoppingcart.auth.domain.entity.User;
import com.shoppingcart.auth.domain.exception.UserAlreadyExistsException;
import com.shoppingcart.auth.domain.vo.Role;

/**
 * Use case that registers a new user and immediately issues a JWT.
 *
 * <p>Execution steps:</p>
 * <ol>
 *   <li>Check for a duplicate e-mail via {@link LoadUserPort}; throw {@link UserAlreadyExistsException} if found.</li>
 *   <li>Construct a {@link User} with the registration constructor, which validates the e-mail and password.</li>
 *   <li>Encode the plain-text password via {@link PasswordEncoderPort}.</li>
 *   <li>Build a second {@link User} instance with the hashed password and persist it via {@link SaveUserPort}.</li>
 *   <li>Generate and return a signed JWT for the newly created user.</li>
 * </ol>
 *
 * <p>Two separate {@link User} objects are used intentionally: the first performs domain validation
 * on the plain-text password; the second carries the hash to the persistence layer.</p>
 */
public class RegisterUserUseCase {

    private final SaveUserPort saveUserPort;
    private final LoadUserPort loadUserPort;
    private final PasswordEncoderPort passwordEncoder;
    private final TokenGeneratorPort tokenGenerator;

    /**
     * @param saveUserPort    output port for persisting the new user
     * @param loadUserPort    output port for duplicate e-mail checks
     * @param passwordEncoder output port for BCrypt hashing
     * @param tokenGenerator  output port for issuing signed JWTs
     */
    public RegisterUserUseCase(SaveUserPort saveUserPort, LoadUserPort loadUserPort,
            PasswordEncoderPort passwordEncoder, TokenGeneratorPort tokenGenerator) {
        this.saveUserPort = saveUserPort;
        this.loadUserPort = loadUserPort;
        this.passwordEncoder = passwordEncoder;
        this.tokenGenerator = tokenGenerator;
    }

    /**
     * Registers the user described by the command and returns a JWT for immediate use.
     *
     * @param command the registration credentials
     * @return a signed JWT token for the newly registered user
     * @throws UserAlreadyExistsException if the e-mail address is already in use
     * @throws com.shoppingcart.auth.domain.exception.InvalidEmailException    if the e-mail format is invalid
     * @throws com.shoppingcart.auth.domain.exception.InvalidPasswordException if the password is shorter than 8 characters
     */
    public String execute(RegisterCommand command) {
        loadUserPort.findByEmail(command.email()).ifPresent(u -> {
            throw new UserAlreadyExistsException(command.email());
        });

        User user = new User(command.email(), command.password());
        String hashedPassword = passwordEncoder.encode(user.getPassword());
        User userToSave = new User(null, user.getEmail(), hashedPassword, Role.USER);

        User saved = saveUserPort.save(userToSave);
        return tokenGenerator.generateToken(saved.getEmail());
    }
}
