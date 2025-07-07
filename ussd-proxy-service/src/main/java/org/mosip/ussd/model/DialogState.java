package org.mosip.ussd.model;

public enum DialogState {
	Start,
	GotId,
	GotOtp,
	GetUIN_VID,
	GetUIN_DownloadCredentials,
	GetUIN_History,
	ResidentMenu,
	ClaimsInput,
	ClaimsMenu,
	GotOTP_TEMPVID,
	GotOtp_DownloadCredentails,
	gotOtp_History,
	GetCredentials,
	GetStatusLog,
	GetTempVid,
	GetPerpetualVid,
	ShareCredentials,
	GotRPPartnerId,
	GotRPApplicationId,
	End
}
