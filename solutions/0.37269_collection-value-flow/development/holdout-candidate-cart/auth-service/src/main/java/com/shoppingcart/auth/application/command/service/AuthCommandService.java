package com.shoppingcart.auth.application.command.service;

import org.springframework.stereotype.Service;

import com.shoppingcart.auth.application.command.dto.LoginCommand;
import com.shoppingcart.auth.application.command.dto.RegisterCommand;
import com.shoppingcart.auth.application.command.port.input.LoginUserPort;
import com.shoppingcart.auth.application.command.port.input.RegisterUserPort;
import com.shoppingcart.auth.application.command.usecase.LoginUserUseCase;
import com.shoppingcart.auth.application.command.usecase.RegisterUserUseCase;

/**
 * Spring-managed service that exposes the command-side authentication use cases as input ports.
 *
 * <p>Acts as a thin orchestrator: it implements both {@link RegisterUserPort} and
 * {@link LoginUserPort} and delegates every call to the corresponding use case object, keeping
 * the use cases free of Spring annotations and fully unit-testable.</p>
 *
 * <p>Both use cases are injected as beans wired in
 * {@link com.shoppingcart.auth.framework.config.ApplicationConfig}.</p>
 */
@Service
public class AuthCommandService implements RegisterUserPort, LoginUserPort {

    private final RegisterUserUseCase registerUseCase;
    private final LoginUserUseCase loginUseCase;

    /**
     * @param registerUseCase use case that handles new user registration
     * @param loginUseCase    use case that handles credential verification and token issuance
     */
    public AuthCommandService(RegisterUserUseCase registerUseCase, LoginUserUseCase loginUseCase) {
        this.registerUseCase = registerUseCase;
        this.loginUseCase = loginUseCase;
    }

    /** {@inheritDoc} */
    @Override
    public String execute(RegisterCommand command) {
        return registerUseCase.execute(command);
    }

    /** {@inheritDoc} */
    @Override
    public String execute(LoginCommand command) {
        return loginUseCase.execute(command);
    }
}
