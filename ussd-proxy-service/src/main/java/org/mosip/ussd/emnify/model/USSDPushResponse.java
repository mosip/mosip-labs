package org.mosip.ussd.emnify.model;

import com.google.gson.annotations.SerializedName;

import lombok.Data;
@Data
public class USSDPushResponse {

	@SerializedName("session-id")
	String session_id;
}
