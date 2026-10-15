package io.mosip.selfregistration.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.mosip.kernel.core.exception.ServiceError;
import io.mosip.selfregistration.dto.SelfRegDto;
import io.mosip.selfregistration.dto.SelfRegResponseDto;
import io.mosip.selfregistration.exception.SelfRegServiceException;
import io.mosip.selfregistration.service.SelfRegistrationService;
import io.mosip.selfregistration.util.SelfRegistrationLogger;
import io.mosip.kernel.core.logger.spi.Logger;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiResponse;
import io.swagger.annotations.ApiResponses;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.Arrays;

@RestController
@Api(value = "This api saves new registration and call idrepo",tags = {"Self Registration"})
public class SelfRegistrationController {

    @Autowired
    SelfRegistrationService selfRegistrationService;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private Environment environment;

    Logger logger = SelfRegistrationLogger.getLogger(SelfRegistrationController.class);

    @PostMapping(path = "/create", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    @ApiResponses(value = { @ApiResponse(code = 200, message = "Request authenticated successfully") })
    public ResponseEntity<?> newRegistration(@RequestBody @Valid SelfRegDto selfRegDto)  {
        logger.info("Request received from client: {}", selfRegDto.getRid());
        SelfRegResponseDto response = new SelfRegResponseDto();
        try {
            response = selfRegistrationService.createRecord(selfRegDto);
            logger.info("Registration successfully initiate.", response.getId());
            return new ResponseEntity<>(response, HttpStatus.OK);
        } catch (SelfRegServiceException e) {
            logger.error("Registration request failed.");
            response.setErrors(Arrays.asList(new ServiceError(e.getErrorCode(),e.getMessage())));
            return new ResponseEntity<>(response, HttpStatus.OK);
        } catch (Exception e) {
            logger.error("Registration request initiation is failed.");
            response.setErrors(Arrays.asList(new ServiceError(e.getMessage(),e.getMessage())));
            return new ResponseEntity<>(response, HttpStatus.BAD_REQUEST);
        }
    }
}
