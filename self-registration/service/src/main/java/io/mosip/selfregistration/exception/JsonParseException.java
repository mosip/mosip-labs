package io.mosip.selfregistration.exception;

import io.mosip.kernel.core.exception.BaseUncheckedException;

public class JsonParseException extends BaseUncheckedException {

    /** The Constant serialVersionUID. */
    private static final long serialVersionUID = 1L;

    /**
     * Instantiates a new parsing exception.
     */
    public JsonParseException() {
        super();
    }

    /**
     * Instantiates a new parsing exception.
     *
     * @param errorMessage the error message
     */
    public JsonParseException(String errorCode,String errorMessage) {
        super(errorCode, errorMessage);
    }

    /**
     * Instantiates a new parsing exception.
     *
     * @param message the message
     * @param cause the cause
     */
    public JsonParseException(String errorCode,String message, Throwable cause) {
        super(errorCode, message, cause);
    }

    public JsonParseException(Exception e) {
    }
}
