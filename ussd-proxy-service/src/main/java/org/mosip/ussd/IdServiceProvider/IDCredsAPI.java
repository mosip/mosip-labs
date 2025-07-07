package org.mosip.ussd.IdServiceProvider;

import okhttp3.ResponseBody;
import retrofit2.Call;
import org.mosip.ussd.IdServiceProvider.models.APIResponse;
import org.mosip.ussd.IdServiceProvider.models.DownloadRequest;
import org.mosip.ussd.IdServiceProvider.models.ResidentCredRequest2;
import org.mosip.ussd.IdServiceProvider.models.ResidentOTPRequest2;
import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;

public interface IDCredsAPI {

    //Methods from Mimoto
    

    @POST("/residentmobileapp/req/otp")
    Call<APIResponse> requestOTP(@Body ResidentOTPRequest2 request);
    @POST("/residentmobileapp/credentialshare/request")
    Call<APIResponse> requestCredentials(@Body ResidentCredRequest2 request);
    @GET("/residentmobileapp/credentialshare/request/status/{requestId}")
    Call<APIResponse> getCredRequestStatus(@Path("requestId") String requestId);
    @POST("/residentmobileapp/credentialshare/download")
    Call<ResponseBody> downloadCredentials(@Body DownloadRequest request);


}
