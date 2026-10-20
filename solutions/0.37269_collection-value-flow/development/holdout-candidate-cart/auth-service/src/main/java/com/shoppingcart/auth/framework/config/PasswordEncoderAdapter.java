package com.shoppingcart.auth.framework.config;

import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import com.shoppingcart.auth.application.command.port.output.PasswordEncoderPort;

/**
 * Output adapter that bridges {@link PasswordEncoderPort} to Spring Security's
 * {@link PasswordEncoder} (BCrypt).
 *
 * <p>Keeps the application layer decoupled from Spring Security by implementing the
 * domain-facing port interface. The underlying {@link PasswordEncoder} bean is a
 * {@code BCryptPasswordEncoder} registered in
 * {@link com.shoppingcart.auth.framework.config.SecurityConfig}.</p>
 */
@Component
public class PasswordEncoderAdapter implements PasswordEncoderPort {

    private final PasswordEncoder passwordEncoder;

    /**
     * @param passwordEncoder Spring Security's {@code BCryptPasswordEncoder} bean
     */
    public PasswordEncoderAdapter(PasswordEncoder passwordEncoder) {
        this.passwordEncoder = passwordEncoder;
    }

    /** {@inheritDoc} */
    @Override
    public String encode(String rawPassword) {
        return passwordEncoder.encode(rawPassword);
    }

    /** {@inheritDoc} */
    @Override
    public boolean matches(String rawPassword, String encodedPassword) {
        return passwordEncoder.matches(rawPassword, encodedPassword);
    }
}
