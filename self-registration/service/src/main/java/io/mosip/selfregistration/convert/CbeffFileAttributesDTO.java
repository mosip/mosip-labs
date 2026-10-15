package io.mosip.selfregistration.convert;

import io.mosip.kernel.biometrics.constant.BiometricType;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CbeffFileAttributesDTO {

    private BiometricType biometricType;
    private FieldFormatRequest fieldFormatRequest;
    private byte[] imageByte;
    private String bioAttribute;
}
