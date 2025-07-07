package org.mosip.ussd.emnify;
import retrofit2.http.Body;
import retrofit2.http.DELETE;
import retrofit2.http.GET;
import retrofit2.http.PATCH;
import retrofit2.http.POST;
import retrofit2.http.Path;

import java.util.List;

import org.mosip.ussd.emnify.model.AuthRequest;
import org.mosip.ussd.emnify.model.AuthResponse;
import org.mosip.ussd.emnify.model.EndPoint;
import org.mosip.ussd.emnify.model.GlobalAPICallback;
import org.mosip.ussd.emnify.model.GlobalAPICallbackReqResp;
import org.mosip.ussd.emnify.model.ServiceProfilePatchRequest;
import org.mosip.ussd.emnify.model.ServiceProfilePatchResponse;
import org.mosip.ussd.emnify.model.USSDPushRequest;
import org.mosip.ussd.emnify.model.USSDPushResponse;

import retrofit2.Call;

public interface RestAPI {

	//https://cdn.emnify.net/api/v1/authenticate
    @POST("/api/v1/authenticate")
    Call<AuthResponse> requestAuthWithSecret(@Body AuthRequest request);
    @GET("/api/v1/endpoint")
	Call<List<EndPoint>> getAllEndPoints();
    
    @PATCH("/api/v1/service_profile/{profile_id}")
    Call<ServiceProfilePatchResponse> setServiceCallback(@Path("profile_id") int profileId, @Body ServiceProfilePatchRequest request);
    @GET("/api/v1/api_callback")
    Call<List<GlobalAPICallback>> getAllIntegrationApiCallbacks();
    
    @DELETE("/api/v1/api_callback/{api_callback_id}")
    Call<Void> deleteIntegrationAPiCallback(@Path("api_callback_id") int callbackId);
    @POST("/api/v1/api_callback")
    Call<GlobalAPICallbackReqResp> createGlobalAPICallback(@Body GlobalAPICallbackReqResp request);
    
    @POST("/api/v1/endpoint/{endpoint_id}/ussd")
    Call<USSDPushResponse> pushUSSDMessage(@Path("endpoint_id") int endpointId, @Body USSDPushRequest request);


}
