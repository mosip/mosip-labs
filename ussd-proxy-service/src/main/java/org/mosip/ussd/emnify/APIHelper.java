package org.mosip.ussd.emnify;


import java.io.IOException;
import java.util.List;

import org.mosip.ussd.emnify.model.AuthRequest;
import org.mosip.ussd.emnify.model.AuthResponse;
import org.mosip.ussd.emnify.model.EndPoint;
import org.mosip.ussd.emnify.model.GlobalAPICallback;
import org.mosip.ussd.emnify.model.GlobalAPICallbackReqResp;

import org.mosip.ussd.emnify.model.ServiceProfilePatchRequest;
import org.mosip.ussd.emnify.model.ServiceProfilePatchResponse;
import org.mosip.ussd.emnify.model.USSDCommand;
import org.mosip.ussd.emnify.model.USSDMessage;
import org.mosip.ussd.emnify.model.USSDPushRequest;
import org.mosip.ussd.emnify.model.USSDPushResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;

import retrofit2.Call;

import retrofit2.Response;


public class APIHelper {
	private static final Logger logger = LoggerFactory.getLogger(APIHelper.class);

	RestAPI apiInterface;
	AuthResponse authToken;
	@Value( "${emnify.apikey}" )
	private String apikey;
	
	List<EndPoint> endpoints = null;
	
	public APIHelper(String urlBase, String apikey) {
		APISetup setup = new APISetup(urlBase);
		this.apikey = apikey;
        apiInterface = setup.getClient().create(RestAPI.class);
	}
	public void auth() {
        Call<AuthResponse> call = apiInterface.requestAuthWithSecret( createAuthReq());
//		 Call<String> call = apiInterface.requestAuthWithSecret( createAuthReq());
        try {
        	Response<AuthResponse> response =call.execute();
        	//Response<String> response =call.execute();
        	if(response.isSuccessful()) {
        		logger.info("auth resp:" + response.raw().networkResponse().toString());
        		APISetup.setToken(response.body().auth_token);
        	}
        	
			//authToken = response.isSuccessful() ? response.body(): null;
			
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
        /*
        call.enqueue(new Callback<AuthResponse>() {

			@Override
			public void onResponse(Call<AuthResponse> call, Response<AuthResponse> response) {

				authToken = response.body();
				logger.info(authToken.getAuth_token());
			}

			@Override
			public void onFailure(Call<AuthResponse> call, Throwable t) {

				logger.error("Auth Request Error:"+t.getMessage());
			}

        });
        */
	}
	public List<EndPoint> getAllEndPoints(/*APICallback cb*/){
		Call<List<EndPoint>> call = apiInterface.getAllEndPoints();
		try {
			Response<List<EndPoint>> response = call.execute();
			if(response.isSuccessful()) {
				endpoints = response.body();
			
			}
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return endpoints;
		/*
        call.enqueue(new Callback<List<EndPoint>>() {

			@Override
			public void onResponse(Call<List<EndPoint>> call, Response<List<EndPoint>> response) {
				endpoints = response.body();
				logger.info("get all end points :"+response.raw().toString());
				
				cb.onSuccess(endpoints);
			}

			@Override
			public void onFailure(Call<List<EndPoint>> call, Throwable t) {

				logger.error("get all end points Error:"+t.getMessage());
				cb.onError(t);
			}

        });
        */
	}
	public boolean setServiceCallback(int serviceProfileId, int cbId) {
		ServiceProfilePatchRequest req = new ServiceProfilePatchRequest();
		req.getApi_callback().setId(cbId);
		Call<ServiceProfilePatchResponse> call =apiInterface.setServiceCallback(serviceProfileId, req );
		try {
			Response<ServiceProfilePatchResponse> resp =  call.execute();
			if(resp.isSuccessful())
				return true;
			
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return false;
	}
	public List<GlobalAPICallback> getAllGlobalAPICallbacks(){
		Call<List<GlobalAPICallback>> call =apiInterface.getAllIntegrationApiCallbacks();
		try {
			Response<List<GlobalAPICallback>> resp= call.execute();
			if(resp.isSuccessful())
				return resp.body();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return null;
	}
	
	public void deleteAllGlobalAPICallbacks() {
		deleteAllGlobalAPICallbacks(getAllGlobalAPICallbacks());
	}
	public void deleteAllGlobalAPICallbacks(List<GlobalAPICallback> lstCBs) {
		if(lstCBs == null )
			return;
		for( GlobalAPICallback cb: lstCBs) {
			logger.info("Delete: cbID="+ cb.getId() + ",Url="+cb.getUrl());
			Call<Void> call = apiInterface.deleteIntegrationAPiCallback(cb.getId());
			try {
				call.execute();
			} catch (IOException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
		}
	}
	public String pushUSSDMessage(int endpointId, String msgbody) {
		
		String response = "";
		USSDPushRequest req = new USSDPushRequest();
		USSDCommand cmd  = new USSDCommand();
		USSDMessage msg = new USSDMessage();
		//cmd.setType("request");
		cmd.setType("notification");
		
		msg.setEncoding("default");
		msg.setBody(msgbody);
		cmd.setMessage(msg);
		req.setCmd(cmd);
		
		logger.info("pushUSSD: req="+  req.toString());
		
		Call<USSDPushResponse> call = apiInterface.pushUSSDMessage(endpointId, req);
		try {
			Response<USSDPushResponse> resp = call.execute();
			response = resp.body().getSession_id();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return response;
	}
	public int createGlobalApiCallback(String url) {
		
		GlobalAPICallbackReqResp req = new GlobalAPICallbackReqResp();
		req.setUrl(url);
		req.setPurpose("USSD POC");
		Call<GlobalAPICallbackReqResp> call =  apiInterface.createGlobalAPICallback( req);
		try {
			Response<GlobalAPICallbackReqResp> resp = call.execute();
			if(resp.isSuccessful()) {
				String strId =   resp.body().getApi_callback_id();
				return Integer.parseInt(strId);
				
			}
						
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	    return 0;
	}
	AuthRequest createAuthReq() {
		AuthRequest request = new AuthRequest();
		//request.setApplication_token(apikey);
		request.application_token = apikey;
		return request;
	}
}
