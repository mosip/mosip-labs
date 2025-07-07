package org.mosip.ussd.emnify.model;

import lombok.Data;

@Data
public class USSDCommand {

	String type;
	USSDMessage message;
}
