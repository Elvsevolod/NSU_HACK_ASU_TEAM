package com.shoppingcart.payment.framework.config;

import java.io.IOException;
import java.util.List;

import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * Servlet filter that validates JWT tokens on every incoming request.
 *
 * <p>Extends {@link OncePerRequestFilter} to guarantee single execution per request.
 * If the {@code Authorization} header is present and starts with {@code Bearer }, the token
 * is extracted and validated via {@link JwtService}. On success, a
 * {@link UsernamePasswordAuthenticationToken} is placed in the {@link SecurityContextHolder},
 * allowing Spring Security to treat the request as authenticated.</p>
 *
 * <p>Requests without a valid {@code Bearer} token are passed down the filter chain
 * unchanged — Spring Security's access rules then decide whether to reject them.</p>
 */
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtService jwtService;

    /**
     * @param jwtService the service used to parse and validate JWT tokens
     */
    public JwtAuthenticationFilter(JwtService jwtService) {
        this.jwtService = jwtService;
    }

    /**
     * Extracts the JWT from the {@code Authorization} header, validates it, and populates
     * the security context if the token is valid.
     *
     * @param request  the incoming HTTP request
     * @param response the HTTP response
     * @param chain    the remaining filter chain
     */
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
            FilterChain chain) throws ServletException, IOException {

        String authHeader = request.getHeader("Authorization");

        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            chain.doFilter(request, response);
            return;
        }

        String token = authHeader.substring(7);
        String email = jwtService.getEmailFromToken(token);

        if (email != null && SecurityContextHolder.getContext().getAuthentication() == null
                && jwtService.isTokenValid(token)) {

            UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
                    email, null, List.of());
            auth.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
            SecurityContextHolder.getContext().setAuthentication(auth);
        }

        chain.doFilter(request, response);
    }
}
