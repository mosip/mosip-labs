package org.mosip.ussd.IdServiceProvider;

import okhttp3.ResponseBody;
import retrofit2.Call;
import org.mosip.ussd.IdServiceProvider.models.APIResponse;
import org.mosip.ussd.IdServiceProvider.models.AuthRequest;
import org.mosip.ussd.IdServiceProvider.models.ChangeOfAddressRequest;

import org.mosip.ussd.IdServiceProvider.models.IDStatusRequest;
import org.mosip.ussd.IdServiceProvider.models.OTPRequest;
import org.mosip.ussd.IdServiceProvider.models.ResidentCredRequest;

import org.mosip.ussd.IdServiceProvider.models.ResidentHistoryRequest;
import org.mosip.ussd.IdServiceProvider.models.ResidentOTPRequest;

import org.mosip.ussd.IdServiceProvider.models.VIDRequest;
import org.mosip.ussd.IdServiceProvider.models.ValidateOTPRequest;

import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;

public interface IDSAPI extends IDCredsAPI{
    /*
     * Get Access token, given client secret and AppId
     */
    @POST("/v1/authmanager/authenticate/clientidsecretkey")
    Call<APIResponse> requestAuthWithSecret(@Body AuthRequest request);

    /*
     *   Pre reg OTP Request
     */
    @POST("/preregistration/v1/login/sendOtp/langcode")
    Call<APIResponse> requestOTP(@Body OTPRequest request);

    /*
     *   Pre reg validate OTP
     */
    @POST("/preregistration/v1/login/validateOtp")
    Call<APIResponse> validateOTP(@Body ValidateOTPRequest request);

    /*
     * Get RID Status
     */
    @POST("/resident/v1/rid/check-status")
    Call<APIResponse> getIDStatus(@Body IDStatusRequest request);

    @POST("/resident/v1/req/otp")
    Call<APIResponse> requestResidentOTP(@Body ResidentOTPRequest request);


    @POST("/resident/v1/req/credential")
    Call<APIResponse> requestResidentCredentials(@Body ResidentCredRequest request);

    @GET("/resident/v1/req/credential/status/{requestId}")
    Call<APIResponse> getResidentCredRequestStatus(@Path("requestId") String requestId);

    @GET("/resident/v1/req/card/{requestId}")
    Call<ResponseBody> downloadResidentCredentials(@Path("requestId") String requestId);


//    @POST("/resident/v1/req/euin")
 //   Call<APIResponse> requestResidentEUIN(@Body ResidentEUINRequest request);

    @POST("/resident/v1/req/auth-history")
    Call<APIResponse> requestAuthHistory(@Body ResidentHistoryRequest request);

    @POST("/resident/v1/req/update-uin")
    Call<APIResponse> requestUpdateDemoData(@Body ChangeOfAddressRequest request);
    @POST("/resident/v1/vid")
    Call<APIResponse> requestVID(@Body VIDRequest request);


}
