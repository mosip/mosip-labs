package io.mosip.selfregistration.convert;

import io.mosip.kernel.biometrics.constant.BiometricType;
import org.jnbis.api.model.Bitmap;
import org.jnbis.internal.WsqDecoder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.awt.image.WritableRaster;
import java.io.*;
import java.util.List;

@Component
public class BioConversion implements BioConvertorApiFactory {

    @Autowired
    BioUtilApplication bioUtilApplication;

    @Override
    public byte[] convertImage(FieldFormatRequest fieldFormatRequest, byte[] imageData, BiometricType biometricType) throws Exception {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        byte[] byteData = imageData;
        List<DataFormat> destFormats = fieldFormatRequest.getDestFormat();
        DataFormat currentFormat = fieldFormatRequest.getSrcFormat();

        for(DataFormat toFormat : destFormats) {
            if(currentFormat.equals(toFormat)) {
               currentFormat = toFormat;
            } else if(currentFormat.equals(DataFormat.JPEG) && !toFormat.equals(DataFormat.JPEG)) {
                ImageIO.write(ImageIO.read(new ByteArrayInputStream(byteData)), toFormat.getFormat(), baos);
                byteData = baos.toByteArray();
                currentFormat = toFormat;
            } else if(currentFormat.equals(DataFormat.WSQ)) {
                WsqDecoder decoder = new WsqDecoder();
                Bitmap bitmap = decoder.decode(byteData);
                int width = bitmap.getWidth();
                int height = bitmap.getHeight();
                byte[] data = bitmap.getPixels();
                BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_BYTE_GRAY);
                WritableRaster raster = image.getRaster();
                raster.setDataElements(0, 0, width, height, data);
                ImageIO.write(image, toFormat.getFormat(), baos);

                byteData = baos.toByteArray();
                currentFormat = toFormat;
            } else if(currentFormat.equals(DataFormat.JP2) || currentFormat.equals(DataFormat.WSQ) || currentFormat.equals(DataFormat.ISO)) {
                Integer inputImageType = null;
                switch(currentFormat.toString()) {
                    case "JP2":
                        inputImageType = 0;
                        break;
                    case "WSQ":
                        inputImageType = 1;
                        break;
                    case "ISO":
                        inputImageType = 2;
                        break;
                }

                Integer convertTo = null;
                switch(toFormat.toString()) {
                    case "ISO":
                        convertTo = 0;
                        break;
                    default:
                        convertTo = 1;
                        break;
                }

//                String bioAttribute = fieldName.split("_")[1];
//                BiometricType biometricType = Biometric.getSingleTypeByAttribute(bioAttribute);

                byteData = bioUtilApplication.imageConversion(inputImageType, convertTo, "UNKNOWN", biometricType, byteData);
                currentFormat = toFormat;
            }
        }

        return byteData;
    }

    @Override
    public byte[] writeFile(String fileName, byte[] imageData, DataFormat toFormat) throws IOException {
        File imagePath = new File(System.getProperty("user.dir") + "/Images");
        if(!imagePath.exists())
            imagePath.mkdirs();

        File bioFile = new File(imagePath.getAbsolutePath() + "/" + fileName + "."+ toFormat.getFileFormat());
        OutputStream os = new FileOutputStream(bioFile);
        os.write(imageData);
        os.close();
        return imageData;
    }
}
