package com.shoppingcart.payment.framework.exceptions;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import com.shoppingcart.payment.domain.exceptions.InvalidPaymentAmountException;
import com.shoppingcart.payment.domain.exceptions.OrderAlreadyPaidException;
import com.shoppingcart.payment.domain.exceptions.OrderNotFoundException;
import com.shoppingcart.payment.domain.exceptions.OrderNotValidForPaymentException;
import com.shoppingcart.payment.domain.exceptions.PaymentAlreadyProcessedException;
import com.shoppingcart.payment.domain.exceptions.PaymentNotFoundException;

import jakarta.servlet.http.HttpServletRequest;

/**
 * Centralized exception handler that translates domain and framework exceptions into
 * standardized {@link ErrorResponseDTO} HTTP responses.
 *
 * <p>Handled exceptions and their HTTP mappings:</p>
 * <ul>
 *   <li>{@link PaymentNotFoundException} → 404 Not Found</li>
 *   <li>{@link OrderNotFoundException} → 404 Not Found</li>
 *   <li>{@link OrderNotValidForPaymentException} → 422 Unprocessable Entity</li>
 *   <li>{@link OrderAlreadyPaidException} → 409 Conflict</li>
 *   <li>{@link PaymentAlreadyProcessedException} → 409 Conflict</li>
 *   <li>{@link InvalidPaymentAmountException} → 400 Bad Request</li>
 *   <li>{@link IllegalArgumentException} → 400 Bad Request</li>
 *   <li>{@link MethodArgumentNotValidException} → 400 Bad Request (with field details)</li>
 *   <li>{@link MissingServletRequestParameterException} → 400 Bad Request</li>
 *   <li>{@link HttpMessageNotReadableException} → 400 Bad Request</li>
 *   <li>{@link Exception} (catch-all) → 500 Internal Server Error</li>
 * </ul>
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final String BAD_REQUEST = "Bad Request";

    /**
     * Handles the case where a payment cannot be found by its ID.
     *
     * @param ex      the thrown exception
     * @param request the current HTTP request
     * @return a 404 response with error code {@code PAYMENT_NOT_FOUND}
     */
    @ExceptionHandler(PaymentNotFoundException.class)
    public ResponseEntity<ErrorResponseDTO> handleNotFound(PaymentNotFoundException ex,
            HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ErrorResponseDTO(
                404, "Not Found", "PAYMENT_NOT_FOUND",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles the case where the referenced order does not exist in the order-service.
     *
     * @param ex      the thrown exception
     * @param request the current HTTP request
     * @return a 404 response with error code {@code ORDER_NOT_FOUND}
     */
    @ExceptionHandler(OrderNotFoundException.class)
    public ResponseEntity<ErrorResponseDTO> handleOrderNotFound(OrderNotFoundException ex,
            HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ErrorResponseDTO(
                404, "Not Found", "ORDER_NOT_FOUND",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles payment attempts for orders in a non-payable state (e.g., CANCELLED or PAID).
     *
     * @param ex      the thrown exception
     * @param request the current HTTP request
     * @return a 422 response with error code {@code ORDER_NOT_VALID_FOR_PAYMENT}
     */
    @ExceptionHandler(OrderNotValidForPaymentException.class)
    public ResponseEntity<ErrorResponseDTO> handleOrderNotValid(OrderNotValidForPaymentException ex,
            HttpServletRequest request) {
        return ResponseEntity.status(422).body(new ErrorResponseDTO(
                422, "Unprocessable Entity", "ORDER_NOT_VALID_FOR_PAYMENT",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles payment attempts for orders that already have an active payment.
     *
     * @param ex      the thrown exception
     * @param request the current HTTP request
     * @return a 409 response with error code {@code ORDER_ALREADY_PAID}
     */
    @ExceptionHandler(OrderAlreadyPaidException.class)
    public ResponseEntity<ErrorResponseDTO> handleOrderAlreadyPaid(OrderAlreadyPaidException ex,
            HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(new ErrorResponseDTO(
                409, "Conflict", "ORDER_ALREADY_PAID",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles attempts to approve, reject, or refund a payment that has already been processed.
     *
     * @param ex      the thrown exception
     * @param request the current HTTP request
     * @return a 409 response with error code {@code PAYMENT_ALREADY_PROCESSED}
     */
    @ExceptionHandler(PaymentAlreadyProcessedException.class)
    public ResponseEntity<ErrorResponseDTO> handleAlreadyProcessed(PaymentAlreadyProcessedException ex,
            HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(new ErrorResponseDTO(
                409, "Conflict", "PAYMENT_ALREADY_PROCESSED",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles invalid payment amounts (zero/negative or mismatched with the order total).
     *
     * @param ex      the thrown exception
     * @param request the current HTTP request
     * @return a 400 response with error code {@code INVALID_PAYMENT_AMOUNT}
     */
    @ExceptionHandler(InvalidPaymentAmountException.class)
    public ResponseEntity<ErrorResponseDTO> handleInvalidAmount(InvalidPaymentAmountException ex,
            HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, "INVALID_PAYMENT_AMOUNT",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles domain invariant violations expressed as {@link IllegalArgumentException}.
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
     * Handles missing required query parameters (e.g., {@code orderId} in GET /api/payments).
     *
     * @param ex      the thrown exception containing the missing parameter name
     * @param request the current HTTP request
     * @return a 400 response with error code {@code MISSING_PARAMETER}
     */
    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<ErrorResponseDTO> handleMissingParam(MissingServletRequestParameterException ex,
            HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, "MISSING_PARAMETER",
                "Required parameter '" + ex.getParameterName() + "' is missing.",
                request.getRequestURI()));
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
