package io.mosip.selfregistration.exception;

import io.mosip.selfregistration.constant.SelfRegistrationErrorCodes;
import io.mosip.kernel.core.exception.BaseCheckedException;


public class ApiNotAccessibleException extends BaseCheckedException {

	/**
	 * 
	 */
	private static final long serialVersionUID = 1L;

	public ApiNotAccessibleException() {
		super(SelfRegistrationErrorCodes.API_NOT_ACCESSIBLE_EXCEPTION.getErrorCode(),
				SelfRegistrationErrorCodes.API_NOT_ACCESSIBLE_EXCEPTION.getErrorMessage());
    }

    public ApiNotAccessibleException(String message) {
		super(SelfRegistrationErrorCodes.API_NOT_ACCESSIBLE_EXCEPTION.getErrorCode(),
                message);
    }

    public ApiNotAccessibleException(Throwable e) {
		super(SelfRegistrationErrorCodes.API_NOT_ACCESSIBLE_EXCEPTION.getErrorCode(),
				SelfRegistrationErrorCodes.API_NOT_ACCESSIBLE_EXCEPTION.getErrorMessage(), e);
    }

    public ApiNotAccessibleException(String errorMessage, Throwable t) {
		super(SelfRegistrationErrorCodes.API_NOT_ACCESSIBLE_EXCEPTION.getErrorCode(), errorMessage, t);
    }


}
