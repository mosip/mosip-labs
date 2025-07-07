package  org.mosip.ussd.IdServiceProvider.models;
import org.mosip.ussd.IdServiceProvider.MOSIPAPIHelper;
import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

public class ChangeOfAddressRequest {
    @SerializedName("id")
    public String id;
    @SerializedName("version")
    public String version;
    @SerializedName("requesttime")
    public String requesttime;


    @SerializedName("request")
    public Request data ;

    public class Request {
        @SerializedName("identityJson")
        public String identityJson ;
        @SerializedName("transactionID")
        public String transactionID ;
        @SerializedName("individualId")
        public String individualId ;
        @SerializedName("individualIdType")
        public String individualIdType ;
        @SerializedName("otp")
        public String otp ;

     
        public void setIdentityJson(IdentityWrapper identity){
            identityJson= new Gson().toJson(identity);
            identityJson = Base64.getEncoder().encodeToString(identityJson.getBytes(StandardCharsets.UTF_8));
        }
    }
  
    public ChangeOfAddressRequest(){
        id = "mosip.resident.updateuin";
        version = "v1";
        data = new Request();
        requesttime = MOSIPAPIHelper.getUTCDateTime(null);
    }

}


