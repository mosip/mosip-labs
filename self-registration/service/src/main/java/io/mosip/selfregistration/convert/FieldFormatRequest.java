package io.mosip.selfregistration.convert;

import lombok.Data;
import lombok.Getter;
import lombok.Setter;

import java.util.List;

@Data
@Getter
@Setter
public class FieldFormatRequest {
    private String fieldName;
    private String primaryField;
    private DataFormat srcFormat;
    private List<DataFormat> destFormat;
    private String fieldToMap;
    private String srcFieldForQualityScore;

    private String staticValue;

    public FieldFormatRequest() { }

    public FieldFormatRequest(DataFormat srcFormat, List<DataFormat> destFormat) {
        this.srcFormat = srcFormat;
        this.destFormat = destFormat;
    }

    public String getFieldNameWithoutSchema(String fieldName){
        if(fieldName.contains(".")) {
            return fieldName.split("\\.")[1].toUpperCase();
        } else {
            return fieldName.toUpperCase();
        }
    }
}
