package io.mosip.selfregistration.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import io.mosip.selfregistration.dto.SelfRegDto;
import io.mosip.selfregistration.dto.SelfRegResponseDto;

/**
 * The Service DigitalCardService.
 */

public interface SelfRegistrationService {

    SelfRegResponseDto createRecord(SelfRegDto selfRegDto) throws Exception;
}
