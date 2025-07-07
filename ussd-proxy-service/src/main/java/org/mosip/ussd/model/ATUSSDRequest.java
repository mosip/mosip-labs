package org.mosip.ussd.model;

import lombok.Data;

@Data
public class ATUSSDRequest {

	private String sessionId;
	private String serviceCode;
	private String phoneNumber;
	private String text;
	private String networkCode;
	
	public String toString() {
		StringBuilder builder = new StringBuilder();
		builder.append("sessionId=" + sessionId +"\n");
		builder.append("serviceCode=" + serviceCode +"\n");
		builder.append("phoneNumber=" + phoneNumber +"\n");
		builder.append("networkCode=" + networkCode +"\n");
		builder.append("text=" + ( text ==null ? "NULL": text) +"\n");
		return builder.toString();
		
	}
	/*
	@Override
	public int hashCode() {
		final int prime = 31;
		int result = 1;
		result = prime * result + ((phoneNumber == null) ? 0 : phoneNumber.hashCode());
		result = prime * result + ((serviceCode == null) ? 0 : serviceCode.hashCode());
		return result;
	}
*/
	
//	phoneNumber=%2B919845024662&serviceCode=%2A384%2A19351%23&text=2&sessionId=ATUid_e98abe79bdfd894a1fab5b44e0473624&networkCode=99999
}

