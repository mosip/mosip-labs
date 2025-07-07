package  org.mosip.ussd.IdServiceProvider.models;

import com.google.gson.annotations.SerializedName;


public class ResidentCredRequest2 {

  
  @SerializedName("individualId")
  public String individualId;
  @SerializedName("individualIdType")
  public String individualIdType;
  @SerializedName("otp")
  public String otp;
  @SerializedName("transactionID")
  public String transactionID;
}
