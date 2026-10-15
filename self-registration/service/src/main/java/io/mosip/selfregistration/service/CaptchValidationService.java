package io.mosip.selfregistration.service;

public interface CaptchValidationService {

    boolean validate(String captchaToken);
}
