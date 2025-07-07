package  org.mosip.ussd.IdServiceProvider.models;
import org.mosip.ussd.IdServiceProvider.MOSIPAPIHelper;

import com.google.gson.annotations.SerializedName;


public class AuthRequest {
    @SerializedName("id")
    public String id;
    @SerializedName("version")
    public String version;
    @SerializedName("requesttime")
    public String requesttime;

    @SerializedName("request")
    public Request data = null;

    public class Request {
        @SerializedName("clientId")
        public String clientId;
        @SerializedName("secretKey")
        public String secretKey;
        @SerializedName("appId")
        public String appId;

    }

    public AuthRequest(){
        data = new Request();
        id="mosip.auth";
        version ="1.0";
        requesttime = MOSIPAPIHelper.getUTCDateTime(null);
    }
}
