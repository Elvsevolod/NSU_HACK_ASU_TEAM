package com.shoppingcart.order.framework.exceptions;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import com.shoppingcart.order.domain.exceptions.InvalidProductException;
import com.shoppingcart.order.domain.exceptions.OrderAlreadyCancelledException;
import com.shoppingcart.order.domain.exceptions.OrderNotFoundException;
import com.shoppingcart.order.domain.exceptions.PriceMismatchException;

import jakarta.servlet.http.HttpServletRequest;

/**
 * Centralized exception handler that translates domain and framework exceptions into
 * standardized {@link ErrorResponseDTO} HTTP responses.
 *
 * <p>Annotated with {@link RestControllerAdvice} so it intercepts exceptions from all
 * {@code @RestController} classes. Each handler method maps a specific exception type to
 * the appropriate HTTP status code and application error code, ensuring a consistent
 * error contract for API consumers.</p>
 *
 * <p>Handled exceptions and their HTTP mappings:</p>
 * <ul>
 *   <li>{@link OrderNotFoundException} → 404 Not Found</li>
 *   <li>{@link OrderAlreadyCancelledException} → 409 Conflict</li>
 *   <li>{@link InvalidProductException} → 400 Bad Request</li>
 *   <li>{@link PriceMismatchException} → 409 Conflict</li>
 *   <li>{@link IllegalArgumentException} → 400 Bad Request</li>
 *   <li>{@link MethodArgumentNotValidException} → 400 Bad Request (with field details)</li>
 *   <li>{@link HttpMessageNotReadableException} → 400 Bad Request</li>
 *   <li>{@link Exception} (catch-all) → 500 Internal Server Error</li>
 * </ul>
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final String BAD_REQUEST = "Bad Request";

    /**
     * Handles the case where an order cannot be found by its ID.
     *
     * @param ex      the thrown exception
     * @param request the current HTTP request, used to populate the response path
     * @return a 404 response with error code {@code ORDER_NOT_FOUND}
     */
    @ExceptionHandler(OrderNotFoundException.class)
    public ResponseEntity<ErrorResponseDTO> handleNotFound(OrderNotFoundException ex,
            HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ErrorResponseDTO(
                404, "Not Found", "ORDER_NOT_FOUND",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles attempts to cancel an order that has already been cancelled.
     *
     * @param ex      the thrown exception
     * @param request the current HTTP request
     * @return a 409 response with error code {@code ORDER_ALREADY_CANCELLED}
     */
    @ExceptionHandler(OrderAlreadyCancelledException.class)
    public ResponseEntity<ErrorResponseDTO> handleAlreadyCancelled(OrderAlreadyCancelledException ex,
            HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(new ErrorResponseDTO(
                409, "Conflict", "ORDER_ALREADY_CANCELLED",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles orders that reference a product that does not exist or is unavailable.
     *
     * @param ex      the thrown exception
     * @param request the current HTTP request
     * @return a 400 response with error code {@code INVALID_PRODUCT}
     */
    @ExceptionHandler(InvalidProductException.class)
    public ResponseEntity<ErrorResponseDTO> handleInvalidProduct(InvalidProductException ex,
            HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(new ErrorResponseDTO(
                400, BAD_REQUEST, "INVALID_PRODUCT",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles orders where the client-supplied price does not match the catalog price.
     *
     * @param ex      the thrown exception
     * @param request the current HTTP request
     * @return a 409 response with error code {@code PRICE_MISMATCH}
     */
    @ExceptionHandler(PriceMismatchException.class)
    public ResponseEntity<ErrorResponseDTO> handlePriceMismatch(PriceMismatchException ex,
            HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(new ErrorResponseDTO(
                409, "Conflict", "PRICE_MISMATCH",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles domain invariant violations expressed as {@link IllegalArgumentException}
     * (e.g., empty order details, invalid quantity).
     *
     * @param ex      the thrown exception
     * @param request the current HTTP request
     * @return a 400 response with error code {@code INVALID_ARGUMENT}
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ErrorResponseDTO> handleIllegalArgument(IllegalArgumentException ex,
            HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, "INVALID_ARGUMENT",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles Bean Validation failures on {@code @Valid}-annotated request bodies.
     * The response includes a list of field-level error messages.
     *
     * @param ex      the thrown exception containing binding result details
     * @param request the current HTTP request
     * @return a 400 response with error code {@code VALIDATION_ERROR} and per-field details
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponseDTO> handleMethodArgumentNotValid(MethodArgumentNotValidException ex,
            HttpServletRequest request) {
        List<String> details = ex.getBindingResult().getFieldErrors().stream()
                .map(e -> e.getField() + ": " + e.getDefaultMessage())
                .toList();
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, "VALIDATION_ERROR",
                "Request fields failed validation.",
                request.getRequestURI(), details));
    }

    /**
     * Handles malformed JSON or unrecognized enum values in the request body.
     *
     * @param ex      the thrown exception
     * @param request the current HTTP request
     * @return a 400 response with error code {@code INVALID_JSON_FORMAT}
     */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResponseDTO> handleNotReadable(HttpMessageNotReadableException ex,
            HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, "INVALID_JSON_FORMAT",
                "The request body has an invalid format or an unsupported value.",
                request.getRequestURI()));
    }

    /**
     * Catch-all handler for any unhandled exception, preventing stack trace leakage to the client.
     *
     * @param ex      the unexpected exception
     * @param request the current HTTP request
     * @return a 500 response with error code {@code INTERNAL_ERROR}
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponseDTO> handleGeneric(Exception ex, HttpServletRequest request) {
        ex.printStackTrace();
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(new ErrorResponseDTO(
                500, "Internal Server Error", "INTERNAL_ERROR",
                "An unexpected error occurred.",
                request.getRequestURI()));
    }
}
