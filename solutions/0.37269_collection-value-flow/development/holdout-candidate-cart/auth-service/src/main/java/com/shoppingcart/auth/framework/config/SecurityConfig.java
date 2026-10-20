package com.shoppingcart.auth.framework.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Spring Security configuration for the auth-service.
 *
 * <p>Security policy:</p>
 * <ul>
 *   <li>Stateless session management — no server-side HTTP session is created or used.</li>
 *   <li>CSRF disabled — not needed for a stateless, token-based API.</li>
 *   <li>Public paths: {@code /api/auth/**} (login/register), {@code /h2-console/**} (dev database),
 *       and {@code /swagger-ui/**} / {@code /v3/api-docs/**} (OpenAPI docs).</li>
 *   <li>All other paths require a valid JWT supplied in the {@code Authorization: Bearer <token>} header.</li>
 *   <li>H2 console frame embedding is enabled by disabling the {@code X-Frame-Options} header.</li>
 * </ul>
 *
 * <p>{@link JwtAuthenticationFilter} is inserted before
 * {@link UsernamePasswordAuthenticationFilter} to populate the {@link org.springframework.security.core.context.SecurityContext}
 * before Spring Security's standard authentication processing.</p>
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtFilter;

    /**
     * @param jwtFilter the filter that validates Bearer tokens on each request
     */
    public SecurityConfig(JwtAuthenticationFilter jwtFilter) {
        this.jwtFilter = jwtFilter;
    }

    /**
     * Configures and returns the security filter chain.
     *
     * @param http the {@link HttpSecurity} builder provided by Spring
     * @return the fully configured {@link SecurityFilterChain}
     */
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) {
        return http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session
                        .sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/api/auth/**").permitAll()
                        .requestMatchers("/h2-console/**").permitAll()
                        .requestMatchers("/swagger-ui/**", "/swagger-ui.html", "/v3/api-docs/**").permitAll()
                        .anyRequest().authenticated())
                .headers(headers -> headers.frameOptions(frame -> frame.disable()))
                .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class)
                .build();
    }

    /**
     * Registers a {@code BCryptPasswordEncoder} bean consumed by {@link PasswordEncoderAdapter}.
     *
     * @return a BCrypt-based {@link PasswordEncoder}
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
