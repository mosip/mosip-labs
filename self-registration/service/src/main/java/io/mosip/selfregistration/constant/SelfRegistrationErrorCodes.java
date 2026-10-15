package io.mosip.selfregistration.constant;

/**
 * The Enum SelfRegistrationErrorCodes.
 */
public enum SelfRegistrationErrorCodes {

	DUPLICATE_EMAIL_EXCEPTION("SELF_ERR-001", "eMailId found as duplicate"),

	REGISTRATION_FAILED_EXCEPTION("SELF_ERR-002", "Registration failed.. try again."),
	/** The api not accessible exception. */
	API_NOT_ACCESSIBLE_EXCEPTION("DCS-001", "API not accessible"),

	/** The datashare exception. */
	DATASHARE_EXCEPTION("DCS-011", "Datashare response is null"),

	DATA_ENCRYPTION_FAILURE_EXCEPTION("DCS-013", "Data Encryption failed"),

	QRCODE_NOT_GENERATED("DCS-019", "Error while generating QR Code"),

	PDF_NOT_GENERATED("DCS-020", "Error while generating PDF for UIN Card"),

	DATA_NOT_FOUND("DCS-021","Applicant Photo Not Found"),

	IDENTITY_NOT_FOUND("DCS-022", "Unable to Find Identity Field in ID JSON"),

	APPLICANT_PHOTO_NOT_SET( "DCS-023", "Error while setting applicant photo"),

	QRCODE_NOT_SET( "DCS-024", "Error while setting qrCode for uin card"),

	TEM_PROCESSING_FAILURE("DCS-025", "The Processing of Template Failed "),

	DIGITAL_CARD_NOT_GENERATED("DCS-026", "Error while generating PDF for Digital Card"),

	DIGITAL_CARD_NOT_CREATED("DCS-027", "Digital Card is not generated try after some time."),
	ATTRIBUTE_NOT_SET( "DCS-028", "Error while setting template attributes for uin card"),

	VC_VERIFICATION_FAILED("DCS-028", "VC verification is failed.");


	/** The error code. */
	private final String errorCode;

	/** The error message. */
	private final String errorMessage;

	/**
	 * Instantiates a new credential service error codes.
	 *
	 * @param errorCode    the error code
	 * @param errorMessage the error message
	 */
	private SelfRegistrationErrorCodes(final String errorCode, final String errorMessage) {
		this.errorCode = errorCode;
		this.errorMessage = errorMessage;
	}

	/**
	 * Gets the error code.
	 *
	 * @return the error code
	 */
	public String getErrorCode() {
		return errorCode;
	}

	/**
	 * Gets the error message.
	 *
	 * @return the error message
	 */
	public String getErrorMessage() {
		return errorMessage;
	}

	/**
	 * Gets the error code and error message.
	 *
	 * @return the error message
	 */
	public String getError() {
		return errorCode+" "+errorMessage;
	}
}
