package io.mosip.selfregistration.service.impl;

import io.mosip.selfregistration.dto.NotificationResponseDTO;
import io.mosip.selfregistration.service.EmailHelperService;
import io.mosip.selfregistration.util.SelfRegistrationLogger;
import io.mosip.selfregistration.util.NotificationUtil;
import io.mosip.kernel.core.logger.spi.Logger;
import org.json.JSONException;
import org.json.JSONObject;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

@Service
public class EmailHelperServiceImpl implements EmailHelperService {

    private Logger logger = SelfRegistrationLogger.getLogger(EmailHelperService.class);

    @Value("${mosip.send.uin.default-emailIds}")
    private String defaultEmailIds;
    @Value("${mosip.idschema.attribute.email:email}")
    private String emailAttribute;

    @Autowired
    private NotificationUtil notificationUtil;

    @Async
    @Override
    public void sendDigitalCardInEmail(JSONObject decryptedCredentialJson, Map<String, Object> attributes,
                                       String emailContentTpl, String emailSubTpl, byte[] pdfBytes) {

        String residentEmailId = "";
        if (decryptedCredentialJson.has(emailAttribute)) {
            try {
                residentEmailId = decryptedCredentialJson.getString(emailAttribute);
            } catch (JSONException e) {
                logger.error("Resident email fetch failed", residentEmailId, e);
            }
        }
        try {
            String rid = (String) attributes.get("rid");
            List<String> emailIds = Arrays.asList(residentEmailId, defaultEmailIds);
            List<NotificationResponseDTO> responseDTOs = notificationUtil.emailNotification(emailIds, rid,
                    emailContentTpl, emailSubTpl, attributes, pdfBytes);
            responseDTOs.forEach(responseDTO ->
                    logger.info("UIN sent successfully via Email, server response..{}", responseDTO)
            );
        } catch (Exception e) {
            logger.error("Failed to send pdf UIN via email.{}", residentEmailId, e);
        }
    }
}
