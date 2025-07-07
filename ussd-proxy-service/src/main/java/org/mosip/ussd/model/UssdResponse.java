package org.mosip.ussd.model;

import lombok.Data;

@Data
public class UssdResponse {
	private String text;
	Commands cmd;
	
}
