package org.mosip.ussd.IdServiceProvider.models;

import com.google.gson.annotations.SerializedName;

import lombok.Data;

@Data
public class DownloadRequest {
    @SerializedName("individualId")
    String individualId;
    @SerializedName("requestId")
    String requestId;
}
