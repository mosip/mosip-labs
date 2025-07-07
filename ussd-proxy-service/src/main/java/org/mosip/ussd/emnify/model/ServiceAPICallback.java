package org.mosip.ussd.emnify.model;

import com.google.gson.annotations.SerializedName;

import lombok.Data;

@Data
public class ServiceAPICallback {
	@SerializedName("id")
	int id;

	@SerializedName("url")
	String url;
}
