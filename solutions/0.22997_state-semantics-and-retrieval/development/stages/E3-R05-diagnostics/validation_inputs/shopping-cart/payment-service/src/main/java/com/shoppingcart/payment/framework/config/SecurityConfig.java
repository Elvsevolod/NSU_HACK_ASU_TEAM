package com.shoppingcart.payment.framework.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Spring Security configuration for the payment-service.
 *
 * <p>Configures a stateless, JWT-based security model:</p>
 * <ul>
 *   <li>CSRF protection is disabled (stateless REST API).</li>
 *   <li>Sessions are never created ({@link SessionCreationPolicy#STATELESS}).</li>
 *   <li>H2 console, actuator, and Swagger UI endpoints are publicly accessible.</li>
 *   <li>All other requests require a valid JWT, enforced by {@link JwtAuthenticationFilter}.</li>
 *   <li>Frame options are disabled to allow the H2 console to render correctly.</li>
 * </ul>
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtFilter;

    /**
     * @param jwtFilter the filter that validates JWT tokens on each request
     */
    public SecurityConfig(JwtAuthenticationFilter jwtFilter) {
        this.jwtFilter = jwtFilter;
    }

    /**
     * Builds and registers the security filter chain.
     *
     * @param http the {@link HttpSecurity} builder provided by Spring Security
     * @return the configured {@link SecurityFilterChain}
     * @throws IllegalStateException if the security configuration fails to build
     */
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) {
        try {
            return http
                    .csrf(csrf -> csrf.disable())
                    .sessionManagement(session -> session
                            .sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                    .authorizeHttpRequests(auth -> auth
                            .requestMatchers("/h2-console/**").permitAll()
                            .requestMatchers("/actuator/**").permitAll()
                            .requestMatchers("/swagger-ui/**", "/swagger-ui.html", "/v3/api-docs/**").permitAll()
                            .anyRequest().authenticated())
                    .headers(headers -> headers.frameOptions(frame -> frame.disable()))
                    .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class)
                    .build();
        } catch (Exception e) {
            throw new IllegalStateException("Security configuration failed", e);
        }
    }
}
