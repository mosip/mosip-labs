package org.mosip.ussd.emnify.model;

import com.google.gson.annotations.SerializedName;

import lombok.Data;
@Data
public class GlobalAPICallbackReqResp {

	@SerializedName("url")
	String url;
	@SerializedName("purpose")
	String purpose;
	
	@SerializedName("api_callback_id")
	String api_callback_id;
}
