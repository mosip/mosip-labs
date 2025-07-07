package  org.mosip.ussd.IdServiceProvider.models;
import org.mosip.ussd.IdServiceProvider.MOSIPAPIHelper;


import com.google.gson.annotations.SerializedName;

public class ResidentHistoryRequest {
    @SerializedName("id")
    public String id;
    @SerializedName("version")
    public String version;
    @SerializedName("requesttime")
    public String requesttime;

    @SerializedName("request")
    public Request data ;
    public class Request {
        @SerializedName("pageFetch")
        public String pageFetch;

        @SerializedName("individualId")
        public String individualId;
        @SerializedName("pageStart")
        public String pageStart;

        @SerializedName("otp")
        public String otp;
        @SerializedName("transactionID")
        public String transactionID;

    }

    public ResidentHistoryRequest(){
        id ="mosip.resident.authhistory";
        version ="v1";
        requesttime = MOSIPAPIHelper.getUTCDateTime(null);
        data = new Request();
    }

}
