package com.shoppingcart.auth.framework.input.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.shoppingcart.auth.application.command.dto.LoginCommand;
import com.shoppingcart.auth.application.command.dto.RegisterCommand;
import com.shoppingcart.auth.application.command.port.input.LoginUserPort;
import com.shoppingcart.auth.application.command.port.input.RegisterUserPort;
import com.shoppingcart.auth.framework.input.dto.AuthResponseDTO;
import com.shoppingcart.auth.framework.input.dto.LoginRequestDTO;
import com.shoppingcart.auth.framework.input.dto.RegisterRequestDTO;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;

/**
 * REST controller (input adapter) exposing the authentication endpoints.
 *
 * <p>All paths are public (no JWT required) as declared in
 * {@link com.shoppingcart.auth.framework.config.SecurityConfig}. Both endpoints return
 * a signed JWT inside an {@link AuthResponseDTO} on success.</p>
 *
 * <p>Depends exclusively on the port interfaces {@link RegisterUserPort} and
 * {@link LoginUserPort}; the concrete implementations are resolved at runtime by Spring.</p>
 */
@Tag(name = "Authentication", description = "User registration and login")
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final RegisterUserPort registerUserPort;
    private final LoginUserPort loginUserPort;

    /**
     * @param registerUserPort input port for the registration use case
     * @param loginUserPort    input port for the login use case
     */
    public AuthController(RegisterUserPort registerUserPort, LoginUserPort loginUserPort) {
        this.registerUserPort = registerUserPort;
        this.loginUserPort = loginUserPort;
    }

    /**
     * Registers a new user account and returns a JWT for immediate use.
     *
     * @param request the registration payload containing e-mail and password
     * @return HTTP 201 Created with a {@link AuthResponseDTO} containing the JWT
     */
    @Operation(summary = "Register a new user")
    @ApiResponse(responseCode = "201", description = "User registered successfully")
    @ApiResponse(responseCode = "400", description = "Invalid request data")
    @PostMapping("/register")
    public ResponseEntity<AuthResponseDTO> register(@Valid @RequestBody RegisterRequestDTO request) {
        String token = registerUserPort.execute(new RegisterCommand(request.email(), request.password()));
        return ResponseEntity.status(HttpStatus.CREATED).body(new AuthResponseDTO(token));
    }

    /**
     * Authenticates an existing user and returns a JWT.
     *
     * @param request the login payload containing e-mail and password
     * @return HTTP 200 OK with a {@link AuthResponseDTO} containing the JWT
     */
    @Operation(summary = "Login with existing credentials")
    @ApiResponse(responseCode = "200", description = "Login successful, returns JWT token")
    @ApiResponse(responseCode = "401", description = "Invalid credentials")
    @PostMapping("/login")
    public ResponseEntity<AuthResponseDTO> login(@Valid @RequestBody LoginRequestDTO request) {
        String token = loginUserPort.execute(new LoginCommand(request.email(), request.password()));
        return ResponseEntity.ok(new AuthResponseDTO(token));
    }
}
