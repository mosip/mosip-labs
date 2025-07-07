package  org.mosip.ussd.IdServiceProvider.models;
import org.mosip.ussd.IdServiceProvider.MOSIPAPIHelper;

import com.google.gson.annotations.SerializedName;

public class OTPRequest {
    @SerializedName("id")
    public String id;
    @SerializedName("version")
    public String version;
    @SerializedName("requesttime")
    public String requesttime;

    @SerializedName("request")
    public Request data = null;

    public class Request {
        @SerializedName("userId")
        public String userId;
        @SerializedName("langCode")

        public String langCode;

    }
  
    public OTPRequest(){
        data = new Request();
        id="mosip.pre-registration.login.sendotp";
        version ="1.0";
        requesttime = MOSIPAPIHelper.getUTCDateTime(null);

    }

}
