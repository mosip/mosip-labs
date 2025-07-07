package org.mosip.ussd.emnify.model;

import com.google.gson.annotations.SerializedName;

import lombok.Data;

@Data
public class USSDPushRequest {

	//@SerializedName("ussd-end")
	@SerializedName("ussd-begin")
	
	USSDCommand cmd;
	
}

