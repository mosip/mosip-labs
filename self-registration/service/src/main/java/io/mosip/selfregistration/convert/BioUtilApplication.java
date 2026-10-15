package io.mosip.selfregistration.convert;

import io.mosip.biometrics.util.ConvertRequestDto;
import io.mosip.biometrics.util.face.FaceDecoder;
import io.mosip.biometrics.util.face.FaceEncoder;
import io.mosip.biometrics.util.finger.FingerDecoder;
import io.mosip.biometrics.util.finger.FingerEncoder;
import io.mosip.biometrics.util.iris.IrisDecoder;
import io.mosip.biometrics.util.iris.IrisEncoder;
import io.mosip.kernel.biometrics.constant.BiometricType;
import io.mosip.kernel.core.logger.spi.Logger;
import io.mosip.selfregistration.util.SelfRegistrationLogger;
import org.springframework.stereotype.Component;

import java.io.FileOutputStream;

/**
 * BioUtilApplication
 *
 */
@Component
public class BioUtilApplication {
	private static final Logger LOGGER = SelfRegistrationLogger.getLogger(BioUtilApplication.class);


	public byte[] imageConversion(Integer imageType, Integer convertTo, String biometricSubType, BiometricType biometricType, byte[] bioValue) {
		// Image Type 0 - JP2000 & 1 - WSQ format
		LOGGER.info("imageConversion :: imageType :: " + (imageType == 0 ? "JP2000" : "WSQ"));

		// ConvertTo 0 - IMAGE_TO_ISO & 1 - ISO_TO_IMAGE
		LOGGER.info("imageConversion :: convertTo :: " + (convertTo == 0 ? "IMAGE_TO_ISO" : "ISO_TO_IMAGE"));

		// Example#Iris Right eye
		LOGGER.info("imageConversion :: biometricSubType :: " + biometricSubType);

		String purpose = "REGISTRATION";
		LOGGER.info("imageConversion :: purpose :: " + purpose);

		LOGGER.info("imageConversion :: Biometric Type :: " + biometricType.value());

		if (biometricType.equals(BiometricType.FACE)) {
			return doFaceConversion(purpose, imageType, convertTo, bioValue);
		} else if (biometricType.equals(BiometricType.IRIS)) {
			if (biometricSubType != null) {
				return doIrisConversion(purpose, imageType, convertTo, biometricSubType, bioValue);
			} else {
				LOGGER.info("imageConversion :: biometricSubType :: " + biometricSubType + " is empty for Iris");
			}
		} else if (biometricType.equals(BiometricType.FINGER)) {
			if (biometricSubType != null) {
				return doFingerConversion(purpose, imageType, convertTo, biometricSubType, bioValue);
			} else {
				LOGGER.info("imageConversion :: biometricSubType :: " + biometricSubType + " is empty for Iris");
			}
		}
		return null;
	}

	public byte[] doFaceConversion(String purpose, Integer inputImageType, Integer convertTo, byte[] imageData) {
		LOGGER.info("doFaceConversion :: Started :: inputImageType ::" + inputImageType + " :: convertTo :: " + convertTo);
		FileOutputStream tmpOutputStream = null;
		try {
			ConvertRequestDto requestDto = new ConvertRequestDto();
			requestDto.setModality("Face");
			requestDto.setPurpose(purpose);
			requestDto.setVersion("ISO19794_5_2011");

			if (convertTo == 0) // Convert JP2000 to Face ISO/IEC 19794-5: 2011
			{
				if (imageData != null) {
					requestDto.setImageType(inputImageType);
					requestDto.setInputBytes(imageData);

					return FaceEncoder.convertFaceImageToISO(requestDto);
				} else {
					LOGGER.error("doFaceConversion :: Could Not convert the Image To ISO ");
				}
			} else if (convertTo == 1) // Convert Face ISO/IEC 19794-5: 2011 to JPG
			{
				requestDto.setInputBytes(imageData);
				requestDto.setOnlyImageInformation(1);

				return FaceDecoder.convertFaceISOToImageBytes(requestDto);
			}
		} catch (Exception ex) {
			LOGGER.info("doFaceConversion :: Error ", ex);
		} finally {
			try {
				if (tmpOutputStream != null)
					tmpOutputStream.close();
			} catch (Exception ex) {
			}
		}
		LOGGER.info("doFaceConversion :: Ended :: ");
		return null;
	}

	public byte[] doIrisConversion(String purpose, Integer inputImageType, Integer convertTo,
			String biometricSubType, byte[] imageData) {
		LOGGER.info("doIrisConversion :: Started :: inputImageType :: " + inputImageType + " :: convertTo ::"
				+ convertTo + " :: biometricSubType :: " + biometricSubType);
		FileOutputStream tmpOutputStream = null;
		try {
			ConvertRequestDto requestDto = new ConvertRequestDto();
			requestDto.setModality("Iris");
			requestDto.setPurpose(purpose);
			requestDto.setVersion("ISO19794_6_2011");

			if (convertTo == 0) // Convert JP2000 to IRIS ISO/IEC 19794-6: 2011
			{
				if (imageData != null) {
					requestDto.setImageType(inputImageType);
					requestDto.setBiometricSubType(biometricSubType);
					requestDto.setInputBytes(imageData);

					return IrisEncoder.convertIrisImageToISO(requestDto);
				} else {
					LOGGER.error("doIrisConversion :: Could Not convert the Image To ISO ");
				}
			} else if (convertTo == 1) // Convert IRIS ISO/IEC 19794-6: 2011 to JPG
			{
				requestDto.setInputBytes(imageData);
				requestDto.setOnlyImageInformation(1);
				return IrisDecoder.convertIrisISOToImageBytes(requestDto);
			}
		} catch (Exception ex) {
			LOGGER.info("doIrisConversion :: Error ", ex);
		} finally {
			try {
				if (tmpOutputStream != null)
					tmpOutputStream.close();
			} catch (Exception ex) {
			}
		}
		LOGGER.info("doIrisConversion :: Ended :: ");
		return null;
	}

	public byte[] doFingerConversion(String purpose, Integer inputImageType, Integer convertTo, String biometricSubType, byte[] imageData) {
		LOGGER.info("doFingerConversion :: Started :: inputImageType :: " + inputImageType + " :: convertTo ::"
				+ convertTo + " :: biometricSubType :: " + biometricSubType);
		FileOutputStream tmpOutputStream = null;
		try {
			ConvertRequestDto requestDto = new ConvertRequestDto();
			requestDto.setModality("Finger");
			requestDto.setPurpose(purpose);
			requestDto.setVersion("ISO19794_4_2011");

			if (convertTo == 0) // Convert JP2000/WSQ to Finger ISO/IEC 19794-4: 2011
			{
				if (imageData != null) {
					requestDto.setImageType(inputImageType);
					requestDto.setBiometricSubType(biometricSubType);
					requestDto.setInputBytes(imageData);

					return FingerEncoder.convertFingerImageToISO(requestDto);
				} else {
					LOGGER.error("doFingerConversion :: Could Not convert the Image To ISO ");
				}
			} else if (convertTo == 1) // Convert Finger ISO/IEC 19794-4: 2011 to JPG/WSQ
			{
					requestDto.setInputBytes(imageData);
					requestDto.setOnlyImageInformation(1);

					return FingerDecoder.convertFingerISOToImageBytes(requestDto);
			}
		} catch (Exception ex) {
			LOGGER.info("doFingerConversion :: Error ", ex);
		} finally {
			try {
				if (tmpOutputStream != null)
					tmpOutputStream.close();
			} catch (Exception ex) {
			}
		}
		LOGGER.info("doFingerConversion :: Ended :: ");
		return null;
	}
}
