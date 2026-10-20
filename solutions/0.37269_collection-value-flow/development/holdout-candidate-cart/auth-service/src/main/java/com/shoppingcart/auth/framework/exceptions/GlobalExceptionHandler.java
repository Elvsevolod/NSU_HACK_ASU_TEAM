package com.shoppingcart.auth.framework.exceptions;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import com.shoppingcart.auth.domain.exception.InvalidEmailException;
import com.shoppingcart.auth.domain.exception.InvalidPasswordException;
import com.shoppingcart.auth.domain.exception.InvalidRoleException;
import com.shoppingcart.auth.domain.exception.UserAlreadyExistsException;
import com.shoppingcart.auth.domain.exception.UserNotFoundException;

import jakarta.servlet.http.HttpServletRequest;

/**
 * Centralised exception handler for the auth-service REST layer.
 *
 * <p>Intercepts exceptions thrown by controllers and use cases and converts them into
 * structured {@link ErrorResponseDTO} responses. Exception-to-HTTP-status mappings:</p>
 * <ul>
 *   <li>{@link com.shoppingcart.auth.domain.exception.UserNotFoundException} → 404 Not Found</li>
 *   <li>{@link com.shoppingcart.auth.domain.exception.UserAlreadyExistsException} → 409 Conflict</li>
 *   <li>{@link com.shoppingcart.auth.domain.exception.InvalidEmailException} → 400 Bad Request</li>
 *   <li>{@link com.shoppingcart.auth.domain.exception.InvalidPasswordException} → 400 Bad Request</li>
 *   <li>{@link com.shoppingcart.auth.domain.exception.InvalidRoleException} → 400 Bad Request</li>
 *   <li>{@link IllegalArgumentException} → 400 Bad Request</li>
 *   <li>{@link org.springframework.web.bind.MethodArgumentNotValidException} → 400 Bad Request (with per-field details)</li>
 *   <li>{@link org.springframework.web.bind.MissingServletRequestParameterException} → 400 Bad Request</li>
 *   <li>{@link org.springframework.http.converter.HttpMessageNotReadableException} → 400 Bad Request</li>
 *   <li>{@link Exception} (catch-all) → 500 Internal Server Error</li>
 * </ul>
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final String BAD_REQUEST = "Bad Request";

    @ExceptionHandler(UserNotFoundException.class)
    public ResponseEntity<ErrorResponseDTO> handleUserNotFound(UserNotFoundException ex,
            HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ErrorResponseDTO(
                404, "Not Found", ex.getCode(),
                ex.getMessage(), request.getRequestURI()));
    }

    @ExceptionHandler(UserAlreadyExistsException.class)
    public ResponseEntity<ErrorResponseDTO> handleUserAlreadyExists(UserAlreadyExistsException ex,
            HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(new ErrorResponseDTO(
                409, "Conflict", ex.getCode(),
                ex.getMessage(), request.getRequestURI()));
    }

    @ExceptionHandler(InvalidEmailException.class)
    public ResponseEntity<ErrorResponseDTO> handleInvalidEmail(InvalidEmailException ex,
            HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, ex.getCode(),
                ex.getMessage(), request.getRequestURI()));
    }

    @ExceptionHandler(InvalidPasswordException.class)
    public ResponseEntity<ErrorResponseDTO> handleInvalidPassword(InvalidPasswordException ex,
            HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, ex.getCode(),
                ex.getMessage(), request.getRequestURI()));
    }

    @ExceptionHandler(InvalidRoleException.class)
    public ResponseEntity<ErrorResponseDTO> handleInvalidRole(InvalidRoleException ex,
            HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, ex.getCode(),
                ex.getMessage(), request.getRequestURI()));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ErrorResponseDTO> handleIllegalArgument(IllegalArgumentException ex,
            HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, "INVALID_ARGUMENT",
                ex.getMessage(), request.getRequestURI()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponseDTO> handleValidation(MethodArgumentNotValidException ex,
            HttpServletRequest request) {
        List<String> details = ex.getBindingResult().getFieldErrors().stream()
                .map(e -> e.getField() + ": " + e.getDefaultMessage())
                .toList();
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, "VALIDATION_ERROR",
                "Request fields failed validation.",
                request.getRequestURI(), details));
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<ErrorResponseDTO> handleMissingParam(MissingServletRequestParameterException ex,
            HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, "MISSING_PARAMETER",
                "Required parameter '" + ex.getParameterName() + "' is missing.",
                request.getRequestURI()));
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResponseDTO> handleNotReadable(HttpMessageNotReadableException ex,
            HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, "INVALID_JSON_FORMAT",
                "The request body has an invalid format or an unsupported value.",
                request.getRequestURI()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponseDTO> handleGeneric(Exception ex, HttpServletRequest request) {
        ex.printStackTrace();
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(new ErrorResponseDTO(
                500, "Internal Server Error", "INTERNAL_ERROR",
                "An unexpected error occurred.",
                request.getRequestURI()));
    }
}
