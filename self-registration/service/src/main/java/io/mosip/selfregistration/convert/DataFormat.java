package io.mosip.selfregistration.convert;

public enum DataFormat {
    JPEG("jpg", "jpg"),
    JP2("jpeg 2000", "jp2"),
    WSQ("wsq","wsq"),
    ISO("ISO", "iso"),
    YMD("yyyy/MM/dd", "yyyy/MM/dd"),
    DMY("dd/MM/yyyy", "dd/MM/yyyy");


    public final String format;
    public final String fileFormat;

    DataFormat(final String format, final String fileFormat) {
        this.format = format;
        this.fileFormat = fileFormat;
    }

    public String getFormat() {
        return format;
    }

    public String getFileFormat() {
        return fileFormat;
    }
}
