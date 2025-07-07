package  org.mosip.ussd.IdServiceProvider.models;
import org.mosip.ussd.IdServiceProvider.MOSIPAPIHelper;
import com.google.gson.annotations.SerializedName;

public class ResidentOTPRequest {

    @SerializedName("id")
    public String id;
    @SerializedName("version")
    public String version;
    @SerializedName("requestTime")
    public String requestTime;

    @SerializedName("individualId")
    public String individualId;
    @SerializedName("individualIdType")
    public String individualIdType;

    @SerializedName("otpChannel")
    public String[] otpChannel;
    @SerializedName("transactionID")
    public String transactionID;
    @SerializedName("metadata")
    public Object metadata;


    public ResidentOTPRequest(){
        id ="mosip.identity.otp.internal";
        version ="1.0";
        requestTime = MOSIPAPIHelper.getUTCDateTime(null);
        metadata = new Object();
    }

}
