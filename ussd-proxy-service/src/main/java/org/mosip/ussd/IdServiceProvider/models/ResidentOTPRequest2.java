package org.mosip.ussd.IdServiceProvider.models;

import com.google.gson.annotations.SerializedName;

public class ResidentOTPRequest2 {
    
    @SerializedName("individualId")
    public String individualId;
    @SerializedName("individualIdType")
    public String individualIdType;
    @SerializedName("otpChannel")
    public String [] otpChannel;

    @SerializedName("transactionID")
    public String transactionID;
    public ResidentOTPRequest2(){
        otpChannel = new String[1];
        otpChannel[0]="EMAIL";
        
    }
}
