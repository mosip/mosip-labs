package io.mosip.selfregistration.util;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.gson.Gson;
import io.mosip.selfregistration.constant.ApiName;
import io.mosip.selfregistration.dto.ErrorDTO;
import io.mosip.selfregistration.dto.NotificationResponseDTO;
import io.mosip.kernel.core.exception.ExceptionUtils;
import io.mosip.kernel.core.http.ResponseWrapper;
import io.mosip.kernel.core.logger.spi.Logger;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.util.StringUtils;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Component
public class NotificationUtil {

    Logger log = SelfRegistrationLogger.getLogger(NotificationUtil.class);

    @Autowired
    private RestClient restApiClient;

    @Autowired
    private TemplateGenerator templateGenerator;

    @Autowired
    private ObjectMapper mapper;

    @Value("${mosip.template-language}")
    private String templateLang;

    private static final Map languageCodes = Map.of("English","eng","français","fra","Española","spa");
    private static final String EMAIL_SUB_DEFAULT = "UIN Card Attached!";
    private static final String EMAIL_DEFAULT = "Your UIN Card is attached.";

    public List<NotificationResponseDTO> emailNotification(List<String> emailIds, String fileName, String emailContentTpl, String emailSubTpl, Map<String, Object> attributes,
                                                           byte[] attachmentFile) throws Exception {
        log.info("sessionId", "idType", "id", "In emailNotification method of NotificationUtil service");
        HttpEntity<byte[]> doc = null;
        String fileText = null;
        MultiValueMap<Object, Object> emailMap = new LinkedMultiValueMap<>();
        if (attachmentFile != null) {
            LinkedMultiValueMap<String, String> pdfHeaderMap = new LinkedMultiValueMap<>();
            pdfHeaderMap.add("Content-disposition",
                    "form-data; name=attachments; filename=" + fileName + ".pdf");
            pdfHeaderMap.add("Content-type", "application/pdf");
            doc = new HttpEntity<>(attachmentFile, pdfHeaderMap);
            emailMap.add("attachments", doc);
        }
        List<NotificationResponseDTO> notifierResponseList = new ArrayList<>();
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        String preferredLang = templateLang;
        if(attributes.containsKey("preferredLang")) {
            preferredLang = (String) attributes.get("preferredLang");
        }
        emailMap.add("mailContent", getEmailContent(emailContentTpl, attributes, preferredLang));
        emailMap.add("mailSubject", getEmailSubject(emailSubTpl, attributes, preferredLang));

        log.info("sessionId", "idType", "id",
                "In emailNotification method of NotificationUtil service emailResourceUrl: " + ApiName.EMAILNOTIFIER);
        emailIds.forEach(emailId -> {
            try {
                notifierResponseList.add(sendEmail(emailId, headers, emailMap));
            } catch (Exception e) {
                log.error("Failed to send notification via email.{}", emailId, e);
            }
        });
        return notifierResponseList;
    }

    private NotificationResponseDTO sendEmail( String emailId, HttpHeaders headers, MultiValueMap<Object, Object> emailMap) throws Exception {
        NotificationResponseDTO notifierResponse = new NotificationResponseDTO();
        try {
            emailMap.set("mailTo", emailId);
            HttpEntity<MultiValueMap<Object, Object>> httpEntity = new HttpEntity<>(emailMap, headers);
            ResponseWrapper response = restApiClient.postApi(ApiName.EMAILNOTIFIER, null, "", "",
                    MediaType.MULTIPART_FORM_DATA, httpEntity, ResponseWrapper.class);
            notifierResponse = mapper.readValue(new Gson().toJson(response.getResponse()), NotificationResponseDTO.class);
            if (notifierResponse != null) {
                if (notifierResponse.getErrors() != null && !notifierResponse.getErrors().isEmpty()) {
                    ErrorDTO error = (ErrorDTO) notifierResponse.getErrors().get(0);
                    log.error("Received failure response from notification service: ", error.getMessage());
                }
            }
        } catch (Exception e) {
            log.error("Error while sending pdf email.", ExceptionUtils.getStackTrace(e));
        }
        return notifierResponse;
    }

    private String getEmailContent(String emailContentTpl, Map<String, Object> attributes, String preferredLang) throws Exception {
        InputStream in = templateGenerator.getTemplate(emailContentTpl, attributes, preferredLang);
        if (in == null) {
            return EMAIL_DEFAULT;
        }
        return new String(in.readAllBytes(), StandardCharsets.UTF_8);
    }

    private String getEmailSubject(String emailSubTpl, Map<String, Object> attributes, String preferredLang) throws Exception {
        InputStream in = templateGenerator.getTemplate(emailSubTpl, attributes, preferredLang);
        if (in == null) {
            return EMAIL_SUB_DEFAULT;
        }
        return new String(in.readAllBytes(), StandardCharsets.UTF_8);
    }

}