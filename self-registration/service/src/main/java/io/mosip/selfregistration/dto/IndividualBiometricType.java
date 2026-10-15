package io.mosip.selfregistration.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.Getter;
import lombok.Setter;

@AllArgsConstructor
@Data
public class IndividualBiometricType {
    private String format;
    private Object version;
    private String value;
}
