package com.shoppingcart.payment.framework.config;

import java.security.Key;
import java.util.Date;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;

/**
 * Service for JWT token parsing and validation within the payment-service.
 *
 * <p>This service only <em>validates</em> tokens — it does not issue them. Tokens are
 * issued by the auth-service and must be signed with the same {@code JWT_SECRET} configured
 * in both services. Uses HMAC-SHA for signature verification via the JJWT library.</p>
 */
@Component
public class JwtService {

    /** The shared signing secret, injected from {@code application.properties}. */
    @Value("${jwt.secret}")
    private String secret;

    /**
     * Extracts the subject (email) from a JWT token.
     *
     * @param token the raw JWT string
     * @return the email address stored as the token subject
     */
    public String getEmailFromToken(String token) {
        return parseClaims(token).getSubject();
    }

    /**
     * Checks whether a JWT token is valid (correctly signed and not expired).
     *
     * @param token the raw JWT string to validate
     * @return {@code true} if the token is valid and not expired, {@code false} otherwise
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
