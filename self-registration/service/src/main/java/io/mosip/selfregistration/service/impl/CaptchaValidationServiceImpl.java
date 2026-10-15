package io.mosip.selfregistration.service.impl;

import io.mosip.kernel.core.logger.spi.Logger;
import io.mosip.selfregistration.dto.CaptchaRequest;
import io.mosip.selfregistration.dto.RequestWrapper;
import io.mosip.selfregistration.dto.ResponseWrapper;
import io.mosip.selfregistration.service.CaptchValidationService;
import io.mosip.selfregistration.util.NotificationUtil;
import io.mosip.selfregistration.util.SelfRegistrationLogger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.RequestEntity;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.web.client.RestTemplate;

import java.net.URI;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;

@Service
public class CaptchaValidationServiceImpl implements CaptchValidationService {

    public static final String UTC_DATETIME_PATTERN = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'";

    Logger log = SelfRegistrationLogger.getLogger(CaptchValidationService.class);

    @Autowired
    private RestTemplate restTemplate;

    @Value("${mosip.ssup.captcha.validator.url:}")
    private String validatorUrl;

    @Value("${mosip.ssup.captcha.module.name:ssup}")
    private String moduleName;
    @Value("${mosip.ssup.captcha.enabled:true}")
    private boolean enabled;

    @Override
    public boolean validate(String captchaToken) {
        try{
      if(!enabled){
          log.warn("captcha validation dissable ");
           return true;
      }
            CaptchaRequest captchaRequest = new CaptchaRequest();
            captchaRequest.setCaptchaToken(captchaToken);
            captchaRequest.setModuleName(moduleName);

            RequestWrapper<CaptchaRequest> requestWrapper = new RequestWrapper<>();
            requestWrapper.setRequestTime(ZonedDateTime.now(ZoneOffset.UTC).format(DateTimeFormatter.ofPattern(UTC_DATETIME_PATTERN)));
            requestWrapper.setRequest(captchaRequest);
            RequestEntity<RequestWrapper<CaptchaRequest>> requestEntity = RequestEntity
                    .post(URI.create(validatorUrl))
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(requestWrapper);

            ResponseEntity<ResponseWrapper> responseEntity = restTemplate.exchange(
                    requestEntity,
                    ResponseWrapper.class);

            if (responseEntity.getStatusCode().is2xxSuccessful() && responseEntity.getBody() != null) {
                ResponseWrapper<?> responseWrapper = (ResponseWrapper<?>) responseEntity.getBody();
                if (responseWrapper != null && responseWrapper.getResponse() != null &&
                        CollectionUtils.isEmpty(responseWrapper.getErrors())) {
                    log.info("Captcha Validation Successful");
                    return true;
                }
                log.error("Errors received from CaptchaService: {}", responseEntity.getBody());
            }
        } catch (Exception e) {
            log.error("Failed to validate captcha", e);
        }
        return false;
    }
}
