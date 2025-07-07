package  org.mosip.ussd.IdServiceProvider.models;
import org.mosip.ussd.IdServiceProvider.MOSIPAPIHelper;


import com.google.gson.annotations.SerializedName;


public class ResidentCredRequest {

    @SerializedName("id")
    public String id;
    @SerializedName("version")
    public String version;
    @SerializedName("requesttime")
    public String requesttime;

    @SerializedName("request")
    public Request data = null;

    public class Request {

        @SerializedName("additionalData")
        public Object additionalData;
      //  public AdditionalData additionalData;
        @SerializedName("credentialType")
        public String credentialType;

        @SerializedName("encrypt")
        public Boolean encrypt;

        @SerializedName("encryptionKey")
        public String encryptionKey;

        @SerializedName("individualId")
        public String individualId;

        @SerializedName("issuer")
        public String issuer;
        @SerializedName("otp")
        public String otp;
        @SerializedName("sharableAttributes")
        public Object[] sharableAttributes;
        @SerializedName("recepiant")
        public String recepiant;
        @SerializedName("transactionID")
        public String transactionID;

        @SerializedName("user")
        public String user;

    }

    public ResidentCredRequest(){
            data = new Request();
            id="";
            version ="v1";
            requesttime = MOSIPAPIHelper.getUTCDateTime(null);
            data.issuer= "mpartner-default-print";
            data.user = "";
           // data.additionalData = new AdditionalData();
           // data.additionalData.registrationId = "111111";
           // data.additionalData.vid = "111111";
            data.additionalData = new Object();
            data.sharableAttributes = new Object[0];
            //data.sharableAttributes[0]= "";
            data.recepiant ="";
            data.encrypt =false;
            data.encryptionKey="";
    }

}
