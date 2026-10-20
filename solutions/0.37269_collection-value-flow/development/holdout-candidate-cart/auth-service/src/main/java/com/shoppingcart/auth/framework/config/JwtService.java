package com.shoppingcart.auth.framework.config;

import java.security.Key;
import java.util.Date;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import com.shoppingcart.auth.application.command.port.output.TokenGeneratorPort;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;

/**
 * JWT utility component that both issues and validates tokens.
 *
 * <p>Implements {@link TokenGeneratorPort} so it can be injected into the application layer
 * as a pure port (without exposing the JWT library). It also exposes two public methods used
 * directly by {@link JwtAuthenticationFilter} for token introspection:</p>
 * <ul>
 *   <li>{@link #getEmailFromToken(String)} — extracts the subject claim.</li>
 *   <li>{@link #isTokenValid(String)} — confirms the token is well-formed and not expired.</li>
 * </ul>
 *
 * <p>Signing uses HMAC-SHA256 with the secret configured in {@code jwt.secret}.
 * Token lifetime is controlled by {@code jwt.expiration} (milliseconds).
 * The same secret must be shared with any service that consumes these tokens
 * (e.g. the payment-service's own {@code JwtService}).</p>
 */
@Component
public class JwtService implements TokenGeneratorPort {

    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.expiration}")
    private long expiration;

    /**
     * {@inheritDoc}
     *
     * <p>Sets the e-mail as the JWT subject, records the current time as {@code iat}, and
     * calculates the expiry from {@code jwt.expiration} milliseconds in the future.</p>
     */
    @Override
    public String generateToken(String email) {
        return Jwts.builder()
                .setSubject(email)
                .setIssuedAt(new Date())
                .setExpiration(new Date(System.currentTimeMillis() + expiration))
                .signWith(signingKey(), SignatureAlgorithm.HS256)
                .compact();
    }

    /**
     * Extracts the subject claim (e-mail) from a JWT.
     *
     * @param token the compact JWT string
     * @return the e-mail stored in the subject claim, or {@code null} if parsing fails
     */
    public String getEmailFromToken(String token) {
        return parseClaims(token).getSubject();
    }

    /**
     * Checks whether the token is well-formed, correctly signed, and not expired.
     *
     * @param token the compact JWT string to validate
     * @return {@code true} if the token is valid and unexpired, {@code false} otherwise
     */
    public boolean isTokenValid(String token) {
        try {
            return !parseClaims(token).getExpiration().before(new Date());
        } catch (Exception e) {
            return false;
        }
    }

    private Claims parseClaims(String token) {
        return Jwts.parserBuilder()
                .setSigningKey(signingKey())
                .build()
                .parseClaimsJws(token)
                .getBody();
    }

    private Key signingKey() {
        return Keys.hmacShaKeyFor(secret.getBytes());
    }
}
