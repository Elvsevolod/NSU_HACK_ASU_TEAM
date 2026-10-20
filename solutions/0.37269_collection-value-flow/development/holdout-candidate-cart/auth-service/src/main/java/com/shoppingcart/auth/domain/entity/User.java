package com.shoppingcart.auth.domain.entity;

import com.shoppingcart.auth.domain.vo.Email;
import com.shoppingcart.auth.domain.vo.Password;
import com.shoppingcart.auth.domain.vo.Role;

/**
 * Domain aggregate root representing a registered user.
 *
 * <p>Two constructors serve distinct lifecycle phases:</p>
 * <ul>
 *   <li><b>Registration constructor</b> {@code User(String, String)} — validates and wraps plain-text
 *       credentials via {@link Email} and {@link Password#ofPlainText(String)}; always assigns
 *       {@link Role#USER}.</li>
 *   <li><b>Reconstitution constructor</b> {@code User(Long, String, String, Role)} — rebuilds the
 *       aggregate from persisted data; skips plain-text length validation by using
 *       {@link Password#ofHash(String)}.</li>
 * </ul>
 *
 * <p>Email is normalised (lower-case, trimmed) inside {@link Email}; password hashing is
 * delegated to the application layer via {@link com.shoppingcart.auth.application.command.port.output.PasswordEncoderPort}.</p>
 */
public class User {

    private Long id;
    private Email email;
    private Password password;
    private Role role;

    /**
     * Creates a new, unpersisted user from plain-text credentials.
     *
     * <p>Validates the e-mail format and enforces the 8-character minimum on the password.
     * Role is fixed to {@link Role#USER}; the caller must invoke
     * {@link #promoteToAdmin()} explicitly to elevate privileges.</p>
     *
     * @param email    the user's e-mail address; must match the regex enforced by {@link Email}
     * @param password the plain-text password; must be at least 8 characters
     * @throws com.shoppingcart.auth.domain.exception.InvalidEmailException    if the e-mail is null or malformed
     * @throws com.shoppingcart.auth.domain.exception.InvalidPasswordException if the password is null or shorter than 8 characters
     */
    public User(String email, String password) {
        this.email = new Email(email);
        this.password = Password.ofPlainText(password);
        this.role = Role.USER;
    }

    /**
     * Reconstitutes a user from persisted data.
     *
     * <p>Accepts an already-hashed password and skips length validation, since the hash
     * was verified at registration time. The supplied {@link Role} is used as-is.</p>
     *
     * @param id       the database-assigned identifier
     * @param email    the stored e-mail address
     * @param password the BCrypt hash stored in the database
     * @param role     the user's current role
     */
    public User(Long id, String email, String password, Role role) {
        this.id = id;
        this.email = new Email(email);
        this.password = Password.ofHash(password);
        this.role = role;
    }

    /**
     * Promotes this user to {@link Role#ADMIN}.
     *
     * <p>No guard is applied against repeated promotion; callers should check the current
     * role if idempotency is required.</p>
     */
    public void promoteToAdmin() {
        this.role = Role.ADMIN;
    }

    /** @return the database-assigned identifier, or {@code null} for an unpersisted user */
    public Long getId() { return id; }

    /** @return the normalised (lower-case, trimmed) e-mail string */
    public String getEmail() { return email.value(); }

    /** @return the password value — plain text before encoding, BCrypt hash after persistence */
    public String getPassword() { return password.value(); }

    /** @return the user's current role */
    public Role getRole() { return role; }

    /**
     * Assigns the database-generated identifier after the user is first persisted.
     *
     * @param id the identifier returned by the persistence layer
     */
    public void setId(Long id) { this.id = id; }
}