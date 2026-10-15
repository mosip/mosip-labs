package io.mosip.selfregistration.convert;

import io.mosip.kernel.biometrics.entities.BIR;
import io.mosip.kernel.biometrics.spi.CbeffUtil;
import io.mosip.kernel.cbeffutil.impl.CbeffImpl;
import io.mosip.kernel.core.util.CryptoUtil;
import org.apache.commons.io.IOUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * * This class helps to create Cbeff file with all the biometrics using CBEFF schema definition.
 * *
 */
@Component
public class CbeffFileCreator {

    private final BioConvertorApiFactory bioConvertorApiFactory;
    private final BIRBuilder birBuilder;
    private final CbeffUtil cbeffUtil;

    @Value("${mosip.kernel.xsdfile}")
    private String cbeffXsd;
    private byte[] xsd;

    public CbeffFileCreator(BioConvertorApiFactory bioConvertorApiFactory, BIRBuilder birBuilder) {
        this.bioConvertorApiFactory = bioConvertorApiFactory;
        this.birBuilder = birBuilder;
        this.cbeffUtil = new CbeffImpl();
    }

    /**
     * CBEFF file creation with all the given modalities using CBEFF schema definition.
     * @param attributesDTOList - list of CBEFF file attributes with biometrics in bytes
     * @return CBEFF file in Base64 encoded format.
     * @throws Exception
     */
    public String createCBEFF(List<CbeffFileAttributesDTO> attributesDTOList) throws Exception {
        List<BIR> birList = new ArrayList<>();
        for (CbeffFileAttributesDTO attributesDTO : attributesDTOList) {
            byte[] convertedImageData = bioConvertorApiFactory.convertImage(attributesDTO.getFieldFormatRequest(),
                    attributesDTO.getImageByte(), attributesDTO.getBiometricType());
            BiometricsDto biometricsDto = new BiometricsDto(attributesDTO.getBioAttribute(), convertedImageData,
                    0);
            birList.add(birBuilder.buildBIR(biometricsDto));
        }
        byte[] bdbBytes = cbeffUtil.createXML(birList, this.xsd);
        return CryptoUtil.encodeToURLSafeBase64(bdbBytes);
    }

    @PostConstruct
    public void loadXSD() throws IOException {
        InputStream inputStream = null;
        try {
            inputStream = new ClassPathResource(cbeffXsd).getInputStream();
            this.xsd = IOUtils.toByteArray(inputStream);
        } catch (Throwable var5) {
            if (inputStream != null) {
                try {
                    inputStream.close();
                } catch (Throwable var4) {
                    var5.addSuppressed(var4);
                }
            }
        }
        if (inputStream != null) {
            inputStream.close();
        }

    }

}
