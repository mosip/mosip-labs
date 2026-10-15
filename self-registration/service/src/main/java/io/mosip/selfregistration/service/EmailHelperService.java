package io.mosip.selfregistration.service;

import org.json.JSONObject;

import java.util.Map;

public interface EmailHelperService {

    /**
     * Email service
     * @param decryptedCredentialJson
     * @param rid
     * @param additionalAttributes
     * @param pdfBytes
     */
    void sendDigitalCardInEmail(JSONObject decryptedCredentialJson, Map<String,Object> additionalAttributes,
                                String emailContentTpl, String emailSubTpl, byte[] pdfBytes);
}
