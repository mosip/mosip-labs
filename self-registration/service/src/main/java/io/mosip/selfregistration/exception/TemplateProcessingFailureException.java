package io.mosip.selfregistration.exception;


import io.mosip.kernel.core.exception.BaseUncheckedException;

/**
 * The Class TemplateProcessingFailureException.
 */
public class TemplateProcessingFailureException extends BaseUncheckedException {

	/** The Constant serialVersionUID. */
	private static final long serialVersionUID = 1L;

	/**
	 * Instantiates a new template processing failure exception.
	 */
	public TemplateProcessingFailureException() {
		super();
	}

	/**
	 * Instantiates a new template processing failure exception.
	 *
	 * @param message
	 *            the message
	 */
	public TemplateProcessingFailureException(String message) {
		super("TPL_PROCESS_FAILED", message);
	}

	/**
	 * Instantiates a new template processing failure exception.
	 *
	 * @param message
	 *            the message
	 * @param cause
	 *            the cause
	 */
	public TemplateProcessingFailureException(String message, Throwable cause) {
		super("TPL_PROCESS_FAILED" + EMPTY_SPACE, message, cause);
	}

}
