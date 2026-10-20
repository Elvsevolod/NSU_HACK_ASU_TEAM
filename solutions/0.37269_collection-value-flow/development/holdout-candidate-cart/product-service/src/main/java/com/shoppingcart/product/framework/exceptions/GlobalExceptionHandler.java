package com.shoppingcart.product.framework.exceptions;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import com.shoppingcart.product.domain.exceptions.ProductNotFoundException;
import com.shoppingcart.product.domain.exceptions.ProductValidationException;

import jakarta.servlet.http.HttpServletRequest;

/**
 * Global exception handler for REST endpoints.
 * 
 * This class provides centralized exception handling across all REST controllers
 * using Spring's @RestControllerAdvice annotation. It intercepts exceptions thrown
 * by the application and converts them into standardized ErrorResponseDTO objects
 * with appropriate HTTP status codes and error information.
 * 
 * The handler manages various exception types including custom domain exceptions
 * and Spring framework exceptions, ensuring consistent error response formatting
 * throughout the API.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final String BAD_REQUEST = "Bad Request";

    /**
     * Handles ProductValidationException thrown during data validation.
     * 
     * Returns a 400 Bad Request response with validation error details.
     * The error code is set to "INVALID_DATA".
     * 
     * @param ex the ProductValidationException that was thrown
     * @param request the HTTP request that caused the exception
     * @return a ResponseEntity containing the formatted error response
     */
    @ExceptionHandler(ProductValidationException.class)
    public ResponseEntity<ErrorResponseDTO> handleValidation(ProductValidationException ex,
            HttpServletRequest request) {
        return ResponseEntity.badRequest().body(new ErrorResponseDTO(
                400, BAD_REQUEST, "INVALID_DATA",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles ProductNotFoundException thrown when a requested product is not found.
     * 
     * Returns a 404 Not Found response with error code "PRODUCT_NOT_FOUND".
     * 
     * @param ex the ProductNotFoundException that was thrown
     * @param request the HTTP request that caused the exception
     * @return a ResponseEntity containing the formatted error response
     */
    @ExceptionHandler(ProductNotFoundException.class)
    public ResponseEntity<ErrorResponseDTO> handleNotFound(ProductNotFoundException ex,
            HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ErrorResponseDTO(
                404, "Not Found", "PRODUCT_NOT_FOUND",
                ex.getMessage(), request.getRequestURI()));
    }

    /**
     * Handles MethodArgumentNotValidException from Spring validation framework.
     * 
     * Returns a 400 Bad Request response with field-level validation error details.
     * Extracts field names and validation messages from the binding result.
     * The error code is set to "VALIDATION_ERROR".
     * 
     * @param ex the MethodArgumentNotValidException containing validation errors
     * @param request the HTTP request that caused the exception
     * @return a ResponseEntity containing the formatted error response with validation details
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
     * Handles HttpMessageNotReadableException from the HTTP message converter.
     * 
     * Returns a 400 Bad Request response when the request body has invalid JSON format
     * or contains unsupported values. The error code is set to "INVALID_JSON_FORMAT".
     * 
     * @param ex the HttpMessageNotReadableException indicating JSON parsing error
     * @param request the HTTP request that caused the exception
     * @return a ResponseEntity containing the formatted error response
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
     * Handles all uncaught exceptions as a fallback handler.
     * 
     * Returns a 500 Internal Server Error response for any unexpected exception.
     * Prints the stack trace for debugging purposes. The error code is set to "INTERNAL_ERROR".
     * 
     * @param ex the Exception that was thrown and not handled by other handlers
     * @param request the HTTP request that caused the exception
     * @return a ResponseEntity containing a generic internal error response
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
