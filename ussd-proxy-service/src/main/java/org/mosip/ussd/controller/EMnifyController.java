package org.mosip.ussd.controller;

import java.util.List;

import org.json.simple.JSONObject;
import org.json.simple.JSONValue;
import org.mosip.ussd.dialog.UssdDialogEmnify;
import org.mosip.ussd.emnify.APIHelper;
import org.mosip.ussd.emnify.model.AuthResponse;
import org.mosip.ussd.emnify.model.EndPoint;
import org.mosip.ussd.model.Commands;
import org.mosip.ussd.model.UssdResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.bind.annotation.RestController;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;



@RestController
public class EMnifyController {
	private static final Logger logger = LoggerFactory.getLogger(EMnifyController.class);

	@Value( "${emnify.callbackbase}" )
	private String callbackUrlBase;
	
	@Value( "${emnify.serviceprofileid}")
	private long serviceProfileId;
	@Value( "${emnify.baseurl}")
	private String apiBaseurl;
	
	@Value( "${emnify.apikey}")
	private String apikey;
	
	String result;

	Object o;
	@PostMapping(path="/emnify/callback")
	public String OnCallback(@RequestBody String req) {
		UssdDialogEmnify dlg = new UssdDialogEmnify();
		UssdResponse retVal = null;
		String retStr = "";
		
		logger.info("Callback :" + req);
		JSONObject reqJson = (JSONObject) JSONValue.parse(req);
		if(reqJson.containsKey("ussd-begin")) {
			JSONObject ussdcmd = (JSONObject) reqJson.get("ussd-begin");
			JSONObject message = (JSONObject) ussdcmd.get ("message");
			JSONObject endpoint  = (JSONObject) ussdcmd.get("endpoint");
			String sessionId = endpoint.get("id").toString();   // (String) ussdcmd.get("session-id");
			String reqcode = message.get("body").toString();
			
			if(reqcode.equals("*100#")) {
				//send the dialog menu
				retVal = dlg.dialog("", sessionId,false);
				JSONObject cmd = new JSONObject();
				JSONObject msg = new JSONObject();
				msg.put("encoding", "default");
				msg.put("body", retVal.getText());
				cmd.put("message", msg);
				JSONObject resp = new JSONObject();
				resp.put("ussd-continue", cmd);
				retStr = resp.toJSONString();
			}
			else
			if(reqcode.startsWith("*101#")) {
				String UIN = "";
				String PIN = "";
				//extract UIN and otp from reqcode
				String []parts = reqcode.split("#");
				if(parts.length >=3) {
					UIN = parts[1];
					PIN = parts[2];
					retVal = dlg.createNewVID(UIN, PIN, sessionId, false);
					JSONObject cmd = new JSONObject();
					JSONObject msg = new JSONObject();
					msg.put("encoding", "default");
					msg.put("body", retVal.getText());
					cmd.put("message", msg);
					JSONObject resp = new JSONObject();
					resp.put("ussd-end", cmd);
					retStr = resp.toJSONString();
				}
				
			}
		}
		else
		if(reqJson.containsKey("ussd-continue")) {
		
			JSONObject ussdcmd = (JSONObject) reqJson.get("ussd-continue");
			JSONObject message = (JSONObject) ussdcmd.get ("message");
			JSONObject endpoint  = (JSONObject) ussdcmd.get("endpoint");
			JSONObject resp = new JSONObject();
			JSONObject cmd = new JSONObject();
			JSONObject msg = new JSONObject();
			msg.put("encoding", "default");

			cmd.put("message", msg);
			
			if(message == null) {
			
				resp.put("ussd-end", cmd);
				msg.put("body", "");
				synchronized(o) {
					o.notify();
				}
				
			}
			else
			{
				String sessionId = endpoint.get("id").toString();   // (String) ussdcmd.get("session-id");
				
				//String sessionId = (String) ussdcmd.get("session-id");
				String txt = message == null ? "" : message.get("body").toString();
				retVal = dlg.dialog(txt, sessionId,false);
				msg.put("body", retVal.getText());
				if(retVal.getCmd() == Commands.CON)
					resp.put("ussd-continue", cmd);
				else
					resp.put("ussd-end", cmd);
			}
			retStr = resp.toJSONString();
		
		}
		logger.info("response :" + retStr);
		
		return retStr;
	}

	void tstgson() {
		String jsonStr = "{\"auth_token\":\"eyJhbGciOiJIUzM4NCJ9.eyJhdWQiOiJcL2FwaVwvdjFcL2F1dGhlbnRpY2F0aW9uIiwiZXNjLmFwcCI6ODg2NiwiYXBpX2tleSI6IiIsImVzYy5vcmciOjE1Mjk5LCJlc2Mub3JnTmFtZSI6Ik1PU0lQIiwiaXNzIjoic3BjLWZyb250ZW5kMTAxQHNwYy1mcm9udGVuZCIsImV4cCI6MTY0NjkyOTk3MSwiaWF0IjoxNjQ2OTE1NTcxfQ.tKY9mxr31PEh9in_mDy3f23Wh4zaIgNfPF-yE0A6kMdq2ZIqfav7zyDvW3Iaac1O\"}";

		  Gson gson = new GsonBuilder()
	                .setLenient()
	                .serializeNulls()
	                .setPrettyPrinting()
	                .create();

		AuthResponse re = gson.fromJson(jsonStr, AuthResponse.class);
		logger.info(re.auth_token);
	}
	@PostMapping(path="/emnify/setup")
	public String emnifySetup() {

		//tstgson();
		Boolean isserviceSet = false;
		
		String callbackUrl = callbackUrlBase + "/emnify/callback";
		APIHelper api = new APIHelper(apiBaseurl,apikey);
		api.auth();
		api.deleteAllGlobalAPICallbacks();
		int cbId = api.createGlobalApiCallback(callbackUrl);
		logger.info("callbackID="+ cbId);
		List<EndPoint> epoints = api.getAllEndPoints();
		for(EndPoint e: epoints) {
			logger.info("endpint: " + e.getId() + ", IMEI="+ e.getImei());
			if(e.getImei() != 0) {
				isserviceSet =api.setServiceCallback(e.getService_profile().getId(), cbId);
			}
		}
		result = isserviceSet ? "SUCCESS": "FAILED";
		return result;
	}
	@PostMapping(path="/emnify/ussd/push")
	public @ResponseBody String emnifyUssdPush(@RequestParam(name="endpoint-id") Integer endpointId) {
	
		
		APIHelper api = new APIHelper(apiBaseurl,apikey);
		api.auth();
		String ret ="";
		o = new Object();
		ret = api.pushUSSDMessage(endpointId,"message part 1\n");
		try {
			synchronized(o) {
				o.wait();
			}
			
			//Thread.sleep(5 * 1000);
		} catch (InterruptedException e) {

		}
		ret += api.pushUSSDMessage(endpointId,"message part 2\n");
		return ret;	
		/*	
		String ussd_begin = "\"type\": \"request\",\r\n"
				+ "    \"message\": {\r\n"
				+ "      \"encoding\": \"default\",\r\n"
				+ "      \"body\": \"welcome USSD\"\r\n"
				+ "}";
		
		String result = "OK";
	
		AuthenticationApi apiInstance = new AuthenticationApi();
		Authentication authbody = new Authentication(); 
		authbody.applicationToken("eyJhbGciOiJIUzM4NCJ9.eyJhdWQiOiJcL2FwaVwvdjFcL2FwcGxpY2F0aW9uX3Rva2VuIiwic3ViIjoic2FuYXRoQG1vc2lwLmlvIiwiZXNjLmFwcHNlY3JldCI6ImNjZDI5MDcwLTlkYmYtNDJkYy1hNjBkLTE4YTRmOGE5MzNiYSIsImVzYy5hcHAiOjg4NjYsImVzYy51c2VyIjoyMTk2MjMsImVzYy5vcmciOjE1Mjk5LCJlc2Mub3JnTmFtZSI6Ik1PU0lQIiwiaXNzIjoic3BjLWZyb250ZW5kMTAxQHNwYy1mcm9udGVuZCIsImlhdCI6MTY0NTcxMDQxNH0.RKwrowyznlke9pIOIzzw39vez62Jq_VoG1vM9Zaht4hivRelS64VYTqsMvD6Kcld");
		try {
			AuthenticationResponse apiresult;

			apiresult = apiInstance.authenticate(authbody);
			//endpoint id: 11772906
			logger.info("Auth result " + apiresult);
			//apiresult.getAuthToken();
			ApiClient defaultClient = apiInstance.getApiClient();
			defaultClient.setAccessToken(apiresult.getAuthToken());
			UssdApi apiUssdInstance = new UssdApi();
			StartingaUSSDDialogrequest body = new StartingaUSSDDialogrequest(); // StartingaUSSDDialogrequest |
			body.setUssdBegin(ussd_begin);
			//device ID : 11772906
			//Integer endpointId = 56; // Integer | The numeric ID of an Endpoint
			//IntegrationsApi apiIntInstance = new IntegrationsApi();
			apiUssdInstance.setApiClient(defaultClient);
			logger.info("USSD Push to endpoint :"+ endpointId);
			StartingaUSSDDialogresponse ussdResult = apiUssdInstance.endpointUssdByIdPost(body, endpointId);
			result = ussdResult.toString();
			
		} catch (ApiException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
			result = e.getMessage();
		}
*/
		//return result;
	}
}
