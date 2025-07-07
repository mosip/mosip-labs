package org.mosip.ussd.emnify.model;

import lombok.Data;

@Data
public class EndPoint {

	int id;
	String name;
	String tags;
	String created;
	String last_updated;
	Status status;
	Id service_profile;
	Id tariff_profile;
	Sim sim;
	
	long imei;
	boolean imei_lock;
	String ip_address;
	Id ip_address_space;
    
}
