package  org.mosip.ussd.IdServiceProvider.models;

import com.google.gson.annotations.SerializedName;


public class ValidateOTPRequest {

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
            @SerializedName("otp")

            public String otp;

        }
        public ValidateOTPRequest(){
            data = new Request();
        }

}

