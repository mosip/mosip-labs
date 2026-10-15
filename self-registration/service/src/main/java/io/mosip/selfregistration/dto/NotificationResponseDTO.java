package io.mosip.selfregistration.dto;

import io.mosip.kernel.core.http.ResponseWrapper;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
public class NotificationResponseDTO extends ResponseWrapper {
    private String status;
    private String message;
}
