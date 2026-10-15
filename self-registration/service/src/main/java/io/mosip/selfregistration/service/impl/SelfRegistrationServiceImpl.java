package io.mosip.selfregistration.service.impl;

import com.fasterxml.jackson.core.JsonParseException;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.gson.Gson;
import io.mosip.kernel.biometrics.constant.BiometricType;
import io.mosip.kernel.core.exception.ExceptionUtils;
import io.mosip.kernel.core.http.ResponseWrapper;
import io.mosip.kernel.core.idgenerator.spi.RidGenerator;
import io.mosip.kernel.core.util.CryptoUtil;
import io.mosip.kernel.core.util.DateUtils;
import io.mosip.kernel.core.util.HMACUtils2;
import io.mosip.kernel.core.util.MathUtils;
import io.mosip.selfregistration.constant.ApiName;
import io.mosip.selfregistration.constant.SelfRegistrationErrorCodes;
import io.mosip.selfregistration.controller.SelfRegistrationController;
import io.mosip.selfregistration.convert.*;
import io.mosip.selfregistration.dto.*;
import io.mosip.selfregistration.entity.SelfRegistrationEntity;
import io.mosip.selfregistration.exception.ApisResourceAccessException;
import io.mosip.selfregistration.exception.SelfRegServiceException;
import io.mosip.selfregistration.repositories.SelfRegistrationRepository;
import io.mosip.selfregistration.service.CaptchValidationService;
import io.mosip.selfregistration.service.SelfRegistrationService;
import io.mosip.selfregistration.service.CardGeneratorService;
import io.mosip.selfregistration.service.EmailHelperService;
import io.mosip.selfregistration.util.*;
import io.mosip.kernel.core.logger.spi.Logger;
import io.mosip.kernel.core.pdfgenerator.exception.PDFGeneratorException;
import org.apache.commons.lang3.math.NumberUtils;
import org.json.JSONException;
import org.json.JSONObject;
import org.json.simple.JSONArray;
import org.json.simple.parser.JSONParser;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;

/**
 * The SelfRegistrationServiceImpl.
 *
 */
@Service
public class SelfRegistrationServiceImpl implements SelfRegistrationService {

    @Autowired
    private CardGeneratorService pdfCardServiceImpl;

    @Autowired
    Utility utility;

    @Autowired
    RestClient restClient;

    @Autowired
    SelfRegistrationRepository selfRegistrationRepository;

    @Autowired
    private EmailHelperService emailHelperService;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private RidGenerator ridGenerator;

    @Autowired
    private CbeffFileCreator cbeffFileCreator;

    @Autowired
    private TokenIDGenerator tokenIDGenerator;

    @Autowired
    private CaptchValidationService captchValidationService;

    /** The Constant VALUE. */
    private static final String VALUE = "value";

    private static final String UIN_CARD_EMAIL_SUB = "RPR_UIN_CARD_EMAIL_SUB";
    private static final String UIN_CARD_EMAIL = "RPR_UIN_CARD_EMAIL";
    private static final String TAN_EMAIL_SUB = "RPR_TAN_EMAIL_SUB";
    private static final String TAN_EMAIL = "RPR_TAN_EMAIL";

    @Value("${mosip.selfregistration.verify.credentials.flag:true}")
    private boolean verifyCredentialsFlag;

    @Value("${mosip.selfregistration.pdf.password.enable.flag:true}")
    private boolean isPasswordProtected;

    @Value("${mosip.selfregistration.email.attachment.enable.flag:false}")
    private Boolean isEmailEnabled;

    @Value("${mosip.selfregistration.credential.type}")
    private String credentialType;

    @Value("${mosip.selfregistration.uincard.password}")
    private String digitalCardPassword;

    @Value("${mosip.template-language}")
    private String templateLang;

    @Value("${mosip.master.machine.reg.id}")
    private String machineId;

    @Value("${mosip.master.machine.reg.center.id}")
    private String centerId;

    @Value("${mosip.id.schema.version}")
    private String idSchemaVersion;

    @Value("${mosip.selfregistration.id.type:TAN}")
    private String idType;

    @Value("${mosip.selfregistration.id.number.length:12}")
    private Long idNumberLength;

    @Value("${mosip.selfregistration.id.number.expiry.duration-years:10}")
    private Long expiryDurationInYears;

    @Value("${mosip.selfregistration.selected-handles:}")
    private String selectedHandles;

    @Value("${mosip.selfregistration.addressFieldName:permanentAddress}")
    private String addressField;

    private final int sequenceLength = 5;

    private static final DateTimeFormatter format = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");
    private final String sequenceFormat = "%0"+sequenceLength+"d";
    private static final String VERSION = "v1";
    private Logger logger = SelfRegistrationLogger.getLogger(SelfRegistrationController.class);

    @Override
    public SelfRegResponseDto createRecord(SelfRegDto selfRegDto) throws Exception {
        if(!captchValidationService.validate(selfRegDto.getCaptchaToken()))
            throw new SelfRegServiceException("invalid_captcha", "invalid_captcha");

        SelfRegResponseDto responseDto = new SelfRegResponseDto();
        try {
            //prepare SelfReg entity and before storing dedupe with emailId and store data into table
            String trimmedEmailId = selfRegDto.getEmail().trim();
            //Optional<SelfRegistrationEntity> optional = selfRegistrationRepository.findByEmailIdAndStatus(trimmedEmailId,"ACTIVE");
           // if (optional.isPresent()) {
//                throw new SelfRegServiceException(SelfRegistrationErrorCodes.DUPLICATE_EMAIL_EXCEPTION.getErrorCode(), SelfRegistrationErrorCodes.DUPLICATE_EMAIL_EXCEPTION.getErrorMessage());
            //}
            SelfRegistrationEntity registration = new SelfRegistrationEntity();
            registration.setRid(generateRegistrationId());
            registration.setName(selfRegDto.getFullName().get(0).getValue());
            registration.setGender(selfRegDto.getGender().get(0).getValue());
            registration.setEmailId(trimmedEmailId);
            registration.setPhone(selfRegDto.getPhone());
            registration.setDob(selfRegDto.getDateOfBirth());
            if (selfRegDto.getAddress() != null) {
                registration.setAddress(selfRegDto.getAddress().get(0).getValue());
            }
//            registration.setLangCode(selfRegDto.getFullName().get(0).getLanguage());
            String preferredLang = templateLang;
            if (selfRegDto.getPreferredLang() != null) {
                preferredLang = selfRegDto.getPreferredLang();
            }
            registration.setLangCode(preferredLang);
            registration.setStatus("NEW");
            registration.setCreateDateTime(LocalDateTime.now(ZoneId.of("UTC")));
            byte[] photo = objectMapper.writeValueAsBytes(selfRegDto.getPhoto());
            registration.setBiometricData(photo);
//            selfRegistrationRepository.save(registration);
            // prepare request to generate UIN.
            String uin = generateUIN();
            // prepare addIdentity request and call idrepo api
            IdRequestDto idRequestDto = prepareIdentityRequest(registration.getRid(), uin, selfRegDto);
            ResponseWrapper responseWrapper = addIdentity(idRequestDto);
            if (responseWrapper != null && responseWrapper.getResponse() != null) {
                logger.info("Add identity success, response: {}", responseWrapper.getResponse());
                registration.setUin(uin);
                registration.setStatus("ACTIVE");
                registration.setIdType(idType);
                registration.setIdNumber(generateRandomID());
                registration.setIssuedOn(LocalDateTime.now(ZoneId.of("UTC")));
                registration.setExpiresOn(LocalDateTime.now(ZoneId.of("UTC")).plusYears(expiryDurationInYears));
                registration.setUpdateDateTime(LocalDateTime.now(ZoneId.of("UTC")));
                registration.setTokenId(tokenIDGenerator.generateTokenID(uin));
                selfRegistrationRepository.save(registration);
                responseDto.setId(registration.getUin());
                responseDto.setResponse(responseWrapper.getResponse());
                responseDto.setResponsetime(responseWrapper.getResponsetime());
                // send notification to registered emailId
                generateUINAndNotify(selfRegDto, registration, uin, idRequestDto);
            } else if (responseWrapper != null && responseWrapper.getErrors() != null) {
                logger.error("Error response received: {}", responseWrapper.getErrors());
                responseDto.setErrors(responseWrapper.getErrors());
            }

        } catch (SelfRegServiceException ex) {
            logger.error("Duplicate identity.", ex);
            throw ex;
        } catch (Exception e) {
            logger.error("Exception while storing registration data." ,e);
            throw new SelfRegServiceException(SelfRegistrationErrorCodes.REGISTRATION_FAILED_EXCEPTION.getErrorCode(), SelfRegistrationErrorCodes.REGISTRATION_FAILED_EXCEPTION.getErrorMessage());
        }
        return responseDto;
    }

    private void generateUINAndNotify(SelfRegDto selfRegDto, SelfRegistrationEntity registration, String uin, IdRequestDto idRequestDto) throws JSONException {
        Map<String, Object> additionalAttributes = Map.of("preferredLang",registration.getLangCode(),
                "fullName", registration.getName(),
                "biometrics", selfRegDto.getPhoto(),
                "uin", uin,
                "rid", registration.getRid());
        JSONObject credentialJson = new JSONObject(new Gson().toJson(idRequestDto.getRequest().getIdentity()));
        generatePDFAndSend(credentialJson, additionalAttributes, registration.getLangCode());
        emailHelperService.sendDigitalCardInEmail(credentialJson, additionalAttributes,
                TAN_EMAIL, TAN_EMAIL_SUB, null);
    }

    private String generateRandomID() {
        return ThreadLocalRandom.current().longs(idNumberLength, 0, 10).mapToObj(String::valueOf)
                .collect(Collectors.joining());
    }

    private IdRequestDto prepareIdentityRequest(String rid, String uin, SelfRegDto selfRegDto) throws JsonProcessingException {

        IdRequestDto idRequestDTO = new IdRequestDto();
        idRequestDTO.setId("mosip.id.create");
        idRequestDTO.setVersion(VERSION);
        RequestDto requestDto = new RequestDto();
        requestDto.setRegistrationId(rid);
        requestDto.setIdentity(getIdentity(uin, selfRegDto));
        requestDto.setDocuments(getBiometricsAndDocuments(selfRegDto));
        idRequestDTO.setRequesttime(DateUtils.getUTCTimeFromDate(new Date()));
        idRequestDTO.setRequest(requestDto);
        return idRequestDTO;
    }

    private Map<String, Object> getIdentity(String uin, SelfRegDto selfRegDto) throws JsonProcessingException {

        Map<String, Object> identity = new HashMap<>();
        identity.put("IDSchemaVersion", NumberUtils.createDouble(idSchemaVersion));        
        identity.put("UIN", uin);
        identity.put("fullName", selfRegDto.getFullName());
        identity.put("gender", selfRegDto.getGender());
        identity.put("email", selfRegDto.getEmail());
        identity.put("preferredLang", selfRegDto.getPreferredLang() == null? "eng": selfRegDto.getPreferredLang());
        identity.put("dateOfBirth", selfRegDto.getDateOfBirth().replaceAll("-","/"));

        if(selectedHandles != null && !selectedHandles.isEmpty()) {
            identity.put("selectedHandles", selectedHandles);
        }       
        if (selfRegDto.getPhone() != null && !selfRegDto.getPhone().isEmpty()) {
            identity.put("phone", selfRegDto.getPhone());
        }
        if (selfRegDto.getAddress() != null && !selfRegDto.getAddress().isEmpty()) {
            identity.put(addressField, selfRegDto.getAddress());
        }
        identity.put("individualBiometrics", getIndvBiometricType());
        return identity;
    }

    private String generateUIN() throws Exception {
        try {
            // UIN generation
            long starttime = System.currentTimeMillis();
            ResponseWrapper response = (ResponseWrapper) restClient.getApi(ApiName.IDREPOGETUIN, null, "", "", ResponseWrapper.class);
            if (response != null && response.getResponse() != null) {
                Map<String, String> responseMap = (Map<String, String>) response.getResponse();
                logger.info("UIN Generation success. {}",  System.currentTimeMillis() - starttime);
                return responseMap.get("uin");
            }
            return null;
        } catch (ApisResourceAccessException e) {
            logger.error(e.getMessage() + " : " + ExceptionUtils.getStackTrace(e));
            throw e;
        }
    }

    private ResponseWrapper addIdentity(IdRequestDto idRequestDto) throws Exception {
        logger.debug("Add Identity Request: {}", (new Gson()).toJson(idRequestDto));
        try {

            ResponseWrapper response = (ResponseWrapper) restClient.postApi(ApiName.IDREPOPOSTID,
                    null, "", "", MediaType.APPLICATION_JSON, idRequestDto, ResponseWrapper.class);
            logger.info("Add Identity call completed.");
            return response;
        } catch (ApisResourceAccessException e) {
            logger.error( e.getMessage() + " - " + ExceptionUtils.getStackTrace(e));
            throw e;
        }
    }
    private List<SimpleType> getSimpleTypeObj (String langCode, String value) {
        return Arrays.asList(new SimpleType(langCode, value));
    }

    private IndividualBiometricType getIndvBiometricType () {
        return new IndividualBiometricType("cbeff", 1.0, "individualBiometrics_bio_CBEFF");
    }

    private List<Documents> getBiometricsAndDocuments(SelfRegDto selfRegDto) {
        long starttime = System.currentTimeMillis();
        List<Documents> documents = new ArrayList<>();
        if (selfRegDto.getPhoto() != null) {
            try {
                String base64Image = selfRegDto.getPhoto().replace("data:image/png;base64,", "");
                base64Image = base64Image.replace("data:image/jpeg;base64,", "");
                List<CbeffFileAttributesDTO> attributesDTOList = Arrays.asList(getCbeffFileAttributesDTO(base64Image, DataFormat.JPEG, BiometricType.FACE));
                String encodedCbeffFile = cbeffFileCreator.createCBEFF(attributesDTOList);
                logger.info("file conversion time : {}", System.currentTimeMillis() - starttime);
                documents.add(new Documents("individualBiometrics", encodedCbeffFile));
            } catch (Exception e) {
                logger.error("Error while creating cbeff file.", e);
            }
        }
        return documents;
    }

    private CbeffFileAttributesDTO getCbeffFileAttributesDTO(String base64Image, DataFormat wsq, BiometricType finger) {
        CbeffFileAttributesDTO attributesDTO = new CbeffFileAttributesDTO();
        FieldFormatRequest fieldFormatRequest = new FieldFormatRequest();
        fieldFormatRequest.setDestFormat(Arrays.asList(DataFormat.JP2, DataFormat.ISO));
        fieldFormatRequest.setSrcFormat(wsq);
        attributesDTO.setBiometricType(finger);
        attributesDTO.setImageByte(javax.xml.bind.DatatypeConverter.parseBase64Binary(base64Image));
        attributesDTO.setFieldFormatRequest(fieldFormatRequest);
        attributesDTO.setBioAttribute(Biometric.FACE.getAttributeName());
        return attributesDTO;
    }

    private void generatePDFAndSend(JSONObject decryptedCredentialJson, Map<String, Object> additionalAttributes,
                                    String preferredLang) {

        String password=null;
        try {

            if (isPasswordProtected) {
                password = getPassword(decryptedCredentialJson, preferredLang);
            }
            byte[] pdfBytes = pdfCardServiceImpl.generateCard(decryptedCredentialJson, credentialType, password, additionalAttributes);
            if (isEmailEnabled) {
                // Send digital Card Pdf to Email
                emailHelperService.sendDigitalCardInEmail(decryptedCredentialJson, additionalAttributes,
                        UIN_CARD_EMAIL, UIN_CARD_EMAIL_SUB, pdfBytes);
            }
        } catch (PDFGeneratorException e) {
            logger.error(SelfRegistrationErrorCodes.PDF_NOT_GENERATED.getErrorMessage() ,e);
        } catch (JsonParseException | JsonMappingException e) {
            logger.error(SelfRegistrationErrorCodes.ATTRIBUTE_NOT_SET.getErrorMessage() ,e);
        } catch (Exception e) {
            logger.error(SelfRegistrationErrorCodes.DIGITAL_CARD_NOT_GENERATED.getErrorMessage() , e);
            throw new SelfRegServiceException(SelfRegistrationErrorCodes.DIGITAL_CARD_NOT_GENERATED.getErrorCode(), SelfRegistrationErrorCodes.DIGITAL_CARD_NOT_GENERATED.getErrorMessage());
        }
    }
    /**
     * Gets the password.
     *
     * @param jsonObject
     * @return
     * @throws Exception
     */
    private String getPassword(JSONObject jsonObject, String preferredLang) throws Exception {
        String[] attributes = digitalCardPassword.split("\\|");
        List<String> list = new ArrayList<>(Arrays.asList(attributes));

        Iterator<String> it = list.iterator();
        String uinCardPd = "";
        Object obj=null;
        while (it.hasNext()) {
            String key = it.next().trim();

            Object object = jsonObject.get(key);
            if (object != null) {
                try {
                    obj = new JSONParser().parse(object.toString());
                } catch (Exception e) {
                    obj = object;
                }
            }
            if (obj instanceof JSONArray) {
                // JSONArray node = JsonUtil.getJSONArray(demographicIdentity, value);
                SimpleType[] jsonValues = Utility.mapJsonNodeToJavaObject(SimpleType.class, (JSONArray) obj);
                uinCardPd = uinCardPd.concat(getFormattedPasswordAttribute(getParameter(jsonValues, preferredLang)).substring(0,4));
            } else if (object instanceof org.json.simple.JSONObject) {
                org.json.simple.JSONObject json = (org.json.simple.JSONObject) object;
                uinCardPd = uinCardPd.concat((String) json.get(VALUE));
            } else {
                uinCardPd = uinCardPd.concat(getFormattedPasswordAttribute((String) object.toString()).substring(0,4));
            }
        }
        return uinCardPd.toUpperCase();
    }

    private String getFormattedPasswordAttribute(String password){
        if(password.length()==3){
            return password=password.concat(password.substring(0,1));
        }else if(password.length()==2){
            return password=password.repeat(2);
        }else if(password.length()==1) {
            return password=password.repeat(4);
        }else {
            return password;
        }
    }

    /**
     * Gets the parameter.
     *
     * @param jsonValues
     *            the json values
     * @param langCode
     *            the lang code
     * @return the parameter
     */
    private String getParameter(SimpleType[] jsonValues, String langCode) {

        String parameter = null;
        if (jsonValues != null) {
            for (int count = 0; count < jsonValues.length; count++) {
                String lang = jsonValues[count].getLanguage();
                if (langCode.contains(lang)) {
                    parameter = jsonValues[count].getValue();
                    break;
                }
            }
        }
        return parameter;
    }

    public static String getHMACHashCode(String value) throws NoSuchAlgorithmException {
        if (value == null)
            return null;
        return CryptoUtil.encodeToURLSafeBase64(HMACUtils2.generateHash(value.getBytes()));
    }

    private synchronized String generateRegistrationId() throws InterruptedException {

        int sequenceId = MathUtils.getPow(10, sequenceLength) - 1;
        String randomDigitRid = String.format(sequenceFormat, sequenceId);
        return appendString(randomDigitRid, getcurrentTimeStamp(), centerId, machineId);
    }
    /**
     * This method gets the current timestamp in yyyyMMddHHmmss format.
     *
     * @return current timestamp in fourteen digits
     */
    private String getcurrentTimeStamp() {
        return LocalDateTime.now(ZoneId.of("UTC")).format(format);
    }

    private String appendString(String randomDigitRid, String currentTimeStamp, String centreId, String dongleId) {
        return new StringBuilder().append(centreId)
                .append(dongleId)
                .append(randomDigitRid)
                .append(currentTimeStamp).toString().trim();
    }
}
