package com.shoppingcart.auth.framework.config;

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
 * Servlet filter that validates the JWT on every incoming request exactly once.
 *
 * <p>Extends {@link OncePerRequestFilter} to guarantee single execution per request regardless
 * of filter-chain configuration. The processing logic is:</p>
 * <ol>
 *   <li>Read the {@code Authorization} header; skip filtering if absent or not prefixed with {@code "Bearer "}.</li>
 *   <li>Extract the e-mail subject from the token via {@link JwtService#getEmailFromToken(String)}.</li>
 *   <li>If the email is non-null, no authentication is currently set in the {@link SecurityContextHolder},
 *       and {@link JwtService#isTokenValid(String)} passes, populate the context with a
 *       {@link UsernamePasswordAuthenticationToken} carrying the e-mail as principal and an empty
 *       authorities list (roles are not encoded in the token).</li>
 *   <li>Always delegate to the next filter in the chain.</li>
 * </ol>
 */
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtService jwtService;

    /**
     * @param jwtService service used to extract and validate JWT claims
     */
    public JwtAuthenticationFilter(JwtService jwtService) {
        this.jwtService = jwtService;
    }

    /** {@inheritDoc} */
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
