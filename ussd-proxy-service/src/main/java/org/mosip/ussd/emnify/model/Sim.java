package org.mosip.ussd.emnify.model;

import lombok.Data;

@Data
public class Sim {
	int id;
	long iccid;
	long imsi;
	long msisdn;
	Status status;
	
}
