package io.mosip.selfregistration.exception;

import io.mosip.selfregistration.constant.SelfRegistrationErrorCodes;
import io.mosip.kernel.core.exception.BaseCheckedException;

public class DataShareException  extends BaseCheckedException {

	/**
	 * 
	 */
	private static final long serialVersionUID = 1L;

	public DataShareException() {
		super(SelfRegistrationErrorCodes.DATASHARE_EXCEPTION.getErrorCode(),
				SelfRegistrationErrorCodes.DATASHARE_EXCEPTION.getErrorMessage());
    }

    public DataShareException(String message) {
		super(SelfRegistrationErrorCodes.DATASHARE_EXCEPTION.getErrorCode(),
                message);
    }

    public DataShareException(Throwable e) {
		super(SelfRegistrationErrorCodes.DATASHARE_EXCEPTION.getErrorCode(),
				SelfRegistrationErrorCodes.DATASHARE_EXCEPTION.getErrorMessage(), e);
    }

    public DataShareException(String errorMessage, Throwable t) {
		super(SelfRegistrationErrorCodes.DATASHARE_EXCEPTION.getErrorCode(), errorMessage, t);
    }

}
