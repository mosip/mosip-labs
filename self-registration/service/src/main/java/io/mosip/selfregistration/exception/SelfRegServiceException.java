package io.mosip.selfregistration.exception;

import io.mosip.kernel.core.exception.BaseUncheckedException;

public class SelfRegServiceException extends BaseUncheckedException {

    /**
     *
     */
    private static final long serialVersionUID = 1L;

    public SelfRegServiceException() {
        super();
    }

    public SelfRegServiceException(String message) {
        super("SELF_ERR", message);
    }
    public SelfRegServiceException(String errorCode, String message) {
        super(errorCode, message);
    }
    public SelfRegServiceException(Throwable e) {
        super("SELF_ERR", "SELF_MSG", e);
    }


    public SelfRegServiceException(String errorCode, String message, Throwable e) {
        super(errorCode, message, e);
    }
}
