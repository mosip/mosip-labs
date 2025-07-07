package org.mosip.ussd.util;

import java.io.ByteArrayOutputStream;

import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Base64;
import java.util.TimeZone;

import com.google.zxing.BarcodeFormat;
import com.google.zxing.MultiFormatWriter;
import com.google.zxing.WriterException;
import com.google.zxing.client.j2se.MatrixToImageWriter;
import com.google.zxing.common.BitMatrix;

import org.apache.commons.lang3.RandomStringUtils;



public class Util {
	public static final String ID = "id";
	public static final String OTP = "otp";
	public static final String RPPartnerId = "RPPartnerId";
	public static final String RPApplicationId = "RPAppId";
	public static final String STATE = "state";
	public static final String TrId = "TrId";
	public static final String CREDS_ID="CredsId";

	//public static final String TRID="1234567890";
	public static final String vidType_Perpetual = "Perpetual";
	public static final String vidType_Temporary = "Temporary";
	public static final String ID_TYPE ="UIN";

	//Cred Request States
	public static final String CRED_STATUS_NEW = "NEW";
	public static final String CRED_STATUS_PRINTING = "printing";
	public static final String CRED_STATUS_ISSUED = "ISSUED";
	
	//sroplightendpoints
	public static final String VALIDATE_OTP = "/validate-otp"; 
	public static final String UIN_STATUS = "/auth-lock-status";
	public static final String RID_STATUS = "/rid/check-status";
	public static final String LOCK_UNLOCK = "/%E2%80%8Bauth-lock-unlock"; 


	

	public static String generateQRcode(String data,  String charset, int h, int w) throws WriterException, IOException  
	{  

		BitMatrix matrix = new MultiFormatWriter().encode(new String(data.getBytes(charset), charset), BarcodeFormat.QR_CODE, w, h);  
		//MatrixToImageWriter.writeToPath(matrix,  path.substring(path.lastIndexOf('.') + 1), new File(path));  
		
		 ByteArrayOutputStream bos = new ByteArrayOutputStream();
	        MatrixToImageWriter.writeToStream(matrix, "png", bos);
	        bos.close();

	        return Base64.getEncoder().encodeToString(bos.toByteArray());
	}
	public static byte[] generateQRcodeBytes(String data,  String charset, int h, int w) throws WriterException, IOException  
	{  
		BitMatrix matrix = new MultiFormatWriter().encode(new String(data.getBytes(charset), charset), BarcodeFormat.QR_CODE, w, h);  
		//MatrixToImageWriter.writeToPath(matrix,  path.substring(path.lastIndexOf('.') + 1), new File(path));  
		
		ByteArrayOutputStream bos = new ByteArrayOutputStream();
	    MatrixToImageWriter.writeToStream(matrix, "png", bos);
	    bos.close();

	    return (bos.toByteArray());
	}  
	/* 
	public static  String constructMenu(String[] menuStr, Commands comnd, Boolean bIncludeCmd) {
		String ret ="";
		if(bIncludeCmd)
			ret = comnd.name() +" ";
		for(String s: menuStr)
			ret += s + "\n";
		
		return ret;
	}*/
	public static String getUTCDateTime(LocalDateTime time) {
        String DATEFORMAT = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'";
        DateTimeFormatter dateFormat = DateTimeFormatter.ofPattern(DATEFORMAT);
        if (time == null){
            time = LocalDateTime.now(TimeZone.getTimeZone("UTC").toZoneId());
        }
        String utcTime = time.format(dateFormat);
        return utcTime;
    }
    public static String genRandomNumbers(int targetStringLength) {
        String generatedString = RandomStringUtils.random(targetStringLength, false, true);

        return(generatedString);
    }
	static String extraChars = "[]+";

	public static String stripExtra(String strVal){
		for(int i=0; i < extraChars.length(); i++){
			String extra =  String.valueOf(extraChars.charAt(i));
			strVal = stripExtra(strVal, extra);

		}
		return strVal;
	}
	 static String stripExtra(String strVal, String extraChar){
		//remove starting [ and ending ]
		String val = strVal;
		int stIndex = 0;
		int endIndex ;
		
		val = val.strip();
		endIndex = val.length();

		if(val.startsWith(extraChar))
			stIndex++;
		if(val.endsWith(extraChar))
			endIndex = endIndex - 1;
		val = val.substring(stIndex,endIndex);
		val = val.strip();
		return val;


	}
	public static String MaskString(String s){
		if(s == null)
			return s;

		StringBuilder sb = new StringBuilder();

		for(int n =0; n < s.length(); n++){
			if(n > 3 && n < (s.length()-4) )
				sb.append("X");
			else
				sb.append(s.charAt(n));
		}
		return sb.toString();
	}
	public static String lastPart(String str){
		int pos = str.lastIndexOf ("*");
		if(pos > -1){
			str = str.substring(pos+1).trim();
		}
		return str;
	}
}
