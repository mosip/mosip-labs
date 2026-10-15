package io.mosip.selfregistration.exception;
	
import io.mosip.kernel.core.exception.BaseCheckedException;

/**
 * The Class ApisResourceAccessException.
 * 
 */
public class ApisResourceAccessException extends BaseCheckedException {

	/** The Constant serialVersionUID. */
	private static final long serialVersionUID = 1L;

	/**
	 * Instantiates a new apis resource access exception.
	 */
	public ApisResourceAccessException() {
		super();
	}

	/**
	 * Instantiates a new apis resource access exception.
	 *
	 * @param message the message
	 */
	public ApisResourceAccessException(String errorCode,String message) {
		super(errorCode, message);
	}

	/**
	 * Instantiates a new apis resource access exception.
	 *
	 * @param message the message
	 * @param cause the cause
	 */
	public ApisResourceAccessException(String errorCode,String message, Throwable cause) {
		super(errorCode, message, cause);
	}

	public ApisResourceAccessException(String message) {
		super(message);
	}
}