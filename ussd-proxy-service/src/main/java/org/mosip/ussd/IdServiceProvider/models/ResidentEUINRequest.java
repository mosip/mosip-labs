package  org.mosip.ussd.IdServiceProvider.models;
import org.mosip.ussd.IdServiceProvider.MOSIPAPIHelper;


import com.google.gson.annotations.SerializedName;

public class ResidentEUINRequest {

    @SerializedName("id")
    public String id;
    @SerializedName("version")
    public String version;
    @SerializedName("requesttime")
    public String requestTime;

    @SerializedName("request")
    public Request data ;
    public class Request {
        @SerializedName("cardType")
        public String cardType;

        @SerializedName("individualId")
        public String individualId;
        @SerializedName("individualIdType")
        public String individualIdType;

        @SerializedName("otp")
        public String otp;
        @SerializedName("transactionID")
        public String transactionID;

    }
    public ResidentEUINRequest(){
        id ="mosip.resident.euin";
        version ="v1";
        requestTime = MOSIPAPIHelper.getUTCDateTime(null);
        data = new Request();
    }

}
