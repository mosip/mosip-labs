package org.mosip.ussd.emnify.model;

import com.google.gson.annotations.SerializedName;

import lombok.Data;

@Data
public class ServiceProfilePatchRequest {

	@SerializedName("api_callback")
	ServiceAPICallback api_callback;
	public ServiceProfilePatchRequest() {
		api_callback = new ServiceAPICallback();
	}
}
