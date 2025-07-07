package org.mosip.ussd.emnify.model;

import com.google.gson.annotations.SerializedName;

import lombok.Data;

@Data
public class GlobalAPICallback {

	@SerializedName("organisation_id")
	String organisation_id;
	
	@SerializedName("url")
	String url;
	@SerializedName("created")
	String created;
	@SerializedName("purpose")
	String purpose;
	@SerializedName("id")
	int id;
	
}
