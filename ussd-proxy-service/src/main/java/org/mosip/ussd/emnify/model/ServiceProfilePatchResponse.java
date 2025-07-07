package org.mosip.ussd.emnify.model;

import com.google.gson.annotations.SerializedName;

import lombok.Data;

@Data
public class ServiceProfilePatchResponse {

	@SerializedName("api_callback")
	ServiceAPICallback api_callback;
	@SerializedName("service_profile_id")
	String service_profile_id;
	
}
