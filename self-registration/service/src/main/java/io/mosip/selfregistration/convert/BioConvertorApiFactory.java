package io.mosip.selfregistration.convert;

import io.mosip.kernel.biometrics.constant.BiometricType;

import java.io.IOException;

public interface BioConvertorApiFactory {
    public byte[] convertImage(FieldFormatRequest fieldFormatRequest, byte[] imageData, BiometricType biometricType) throws Exception;
    public byte[] writeFile(String fileName, byte[] imageData, DataFormat toFormat) throws IOException;
}
