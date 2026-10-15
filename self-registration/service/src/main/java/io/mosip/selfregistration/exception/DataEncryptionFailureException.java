package io.mosip.selfregistration.exception;


import io.mosip.selfregistration.constant.SelfRegistrationErrorCodes;
import io.mosip.kernel.core.exception.BaseCheckedException;


public class DataEncryptionFailureException extends BaseCheckedException {

	/** Serializable version Id. */
	private static final long serialVersionUID = 1L;

	public DataEncryptionFailureException() {
		super(SelfRegistrationErrorCodes.DATA_ENCRYPTION_FAILURE_EXCEPTION.getErrorCode(),
				SelfRegistrationErrorCodes.DATA_ENCRYPTION_FAILURE_EXCEPTION.getErrorMessage());
	}

	public DataEncryptionFailureException(Throwable t) {
		super(SelfRegistrationErrorCodes.DATA_ENCRYPTION_FAILURE_EXCEPTION.getErrorCode(),
				SelfRegistrationErrorCodes.DATA_ENCRYPTION_FAILURE_EXCEPTION.getErrorMessage(), t);
	}

	/**
	 * @param message
	 *            Message providing the specific context of the error.
	 * @param cause
	 *            Throwable cause for the specific exception
	 */
	public DataEncryptionFailureException(String message, Throwable cause) {
		super(SelfRegistrationErrorCodes.DATA_ENCRYPTION_FAILURE_EXCEPTION.getErrorCode(), message, cause);

	}

	public DataEncryptionFailureException(String errorMessage) {
		super(SelfRegistrationErrorCodes.DATA_ENCRYPTION_FAILURE_EXCEPTION.getErrorCode(), errorMessage);
	}

}