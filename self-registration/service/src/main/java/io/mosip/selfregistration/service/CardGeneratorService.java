package io.mosip.selfregistration.service;


import org.json.JSONObject;

import java.util.Map;

public interface CardGeneratorService {

	/**
	 * The PDFCardService
	 *
	 * @param decryptedCredentialJson
	 * @param credentialType
	 * @param password
	 * @param additionalAttribute
	 * @return
	 */
	public byte[] generateCard(JSONObject decryptedCredentialJson, String credentialType, String password, Map<String,Object> additionalAttributes) throws Exception;

}