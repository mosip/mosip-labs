package org.mosip.ussd.dialog;

import java.util.HashMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;


import org.mosip.ussd.model.Commands;
import org.mosip.ussd.model.DialogState;
import org.mosip.ussd.model.UssdResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


public class UssdDialogEmnify {

	private static final Logger logger = LoggerFactory.getLogger(UssdDialogEmnify.class);

	static String idJsonSample = "{\"firstName\":\"Jane\",\"lastName\":\"Doe\", \"Gender\":\"Female\",\"dob\":\"1981-02-28\"}";
	static HashMap<String,HashMap<String, String> > stateValues = new HashMap<>();
	//static Hashtable<String, > states = new Hashtable()
	static String[] mainMenu = {
		"Enter VID/UIN"
	};
	static String[] authenticateMenu = {
		"Enter OTP"
	};
	static String[] errorMessage = {
			"Invalid Option"
	};
	static String [] residentServices = {
		"1. Get Credentials",
		"2. Get Temporary VID",
		"3. Get Perpetual VID",
		"4. Get Last 5 Acitities"
	};
	
	//GetCredentials,
	//GetStatusLog,
	//GetTempVid,
	//GetPerpetualVid,
	/*
	 * Dialog launch Request 
	 * 1*<uin/vid value>
	 * 2*<otp value> 
	 * 	validate and return credential JSON
	 */
	public UssdResponse dialog(String cmdText, String sessionId, Boolean bIncludeCmd) {
		UssdResponse ret = new UssdResponse();
		String txt = "";
		HashMap<String, String> state = (HashMap<String, String>) stateValues.get(sessionId);
		if(state == null || cmdText.isEmpty()) {
			txt=  constructMenu(mainMenu, Commands.CON, bIncludeCmd);
			state = new HashMap<>();
			stateValues.put( sessionId, state);
			state.put("state", DialogState.Start.toString());
			ret.setText(txt);
			ret.setCmd(Commands.CON);
		}
		else {
			DialogState st = DialogState.valueOf( state.get("state"));
			String val = "";
			switch(st) { //prev State
				case Start:
					val = cmdText.trim();
					logger.info("Id="+ val);
					state.put("state", DialogState.GotId.toString());
					state.put("Id", val);
					txt = constructMenu(authenticateMenu, Commands.CON, bIncludeCmd);
					ret.setText(txt);
					ret.setCmd(Commands.CON);
					break;
				case GotId:
				{
					//int pos = cmdText.indexOf("*");
					//if(pos > -1){
					//	val = cmdText.substring(pos+1).trim();
					//}
					val = cmdText.trim();
					state.put("state", DialogState.GotOtp.toString());
					state.put("Otp", val);
					logger.info("Otp="+ val);
					txt = constructMenu(residentServices, Commands.CON, bIncludeCmd);
					ret.setText(txt);
					ret.setCmd(Commands.CON);
					//ret = constructMenu(new String[] {idJsonSample},  Commands.END);
					break;
				}
				case GotOtp:
				{
					//cmdText --> Idvalue*otpValue*menuoption
					//int pos = cmdText.indexOf("*");
					//pos = cmdText.indexOf("*", pos+1);
					//val = cmdText.substring(pos+1).trim();
					val = cmdText.trim();
					if(val.equals("1")) {
						//val = Util.generateQRcode(idJsonSample, "UTF-8",200,200);
						txt = constructMenu(new String[] {idJsonSample},  Commands.END, bIncludeCmd);
						
						//txt = constructMenu(new String[] {val},  Commands.END, bIncludeCmd);
						state.put("state", DialogState.GetCredentials.toString());
						ret.setText(txt);
						ret.setCmd(Commands.END);
						
					}
					else
					if(val.equals("2")) {
						txt = constructMenu(new String[] {"984509876543"},  Commands.END, bIncludeCmd);
						state.put("state", DialogState.GetCredentials.toString());
						ret.setText(txt);
						ret.setCmd(Commands.END);	
					}
					else
					if(val.equals("3")) {
						txt = constructMenu(new String[] {"1123987654312345"},  Commands.END, bIncludeCmd);
						state.put("state", DialogState.GetCredentials.toString());
						ret.setText(txt);
						ret.setCmd(Commands.END);
					}
					else
					if(val.equals("4")) {
						txt = constructMenu(new String[] {"Activities list"},  Commands.END, bIncludeCmd);
						state.put("state", DialogState.GetCredentials.toString());
						ret.setText(txt);
						ret.setCmd(Commands.END);
					}

					break;
				}
				case GetCredentials:
					
					txt = constructMenu(new String[] {idJsonSample},  Commands.END, bIncludeCmd);
					ret.setText(txt);
					ret.setCmd(Commands.END);
					break;
				default:
					txt = constructMenu(errorMessage, Commands.END, bIncludeCmd);
					ret.setText(txt);
					ret.setCmd(Commands.END);
					break;
			}
		}
		/**
		if(cmdText == null || cmdText.isBlank()) {
			ret=  constructMenu(mainMenu, Commands.CON);
		}
		else
		if( findMatch(cmdText, "1\\*[0-9]+\\*2\\*[0-9]+")) {	
		//if(cmdText.startsWith("2*")) {
			String otp = cmdText.substring(2);
			HashMap<String, String> state = (HashMap<String, String>) stateValues.get(sessionId);
			if(state == null) {
				ret = constructMenu(errorMessage, Commands.END);
			}
			//trigger call MOSIP generate credentials API
			//construct JSON response and returnt the same
			ret = constructMenu(new String[] {idJsonSample},  Commands.END) ;
		}
		else
			if(cmdText.startsWith("1*")) {
				String idStr = cmdText.substring(2);
				HashMap<String, String> state = (HashMap<String, String>) stateValues.get(sessionId);
				if(state == null) {
					state = new HashMap<>();
					stateValues.put( sessionId, state);
				}
				state.put("uin", idStr);
				//trigger MOSIP otp authentication
				ret = constructMenu(authenticateMenu, Commands.CON);
		}
		else
			ret = constructMenu(errorMessage, Commands.END);
		*/		
		return ret;
	}
	public String constructMenu(String[] menuStr, Commands comnd, Boolean bIncludeCmd) {
		String ret ="";
		if(bIncludeCmd)
			ret = comnd.name() +" ";
		for(String s: menuStr)
			ret += s + "\n";
		
		return ret;
	}
	public Boolean findMatch(String input, String pat) {
		
		Pattern pattern = Pattern.compile(pat);
	    Matcher matcher = pattern.matcher(input);
	    return matcher.matches();
	    
	}
	public UssdResponse createNewVID(String UIN, String otp,String sessionId, Boolean bIncludeCmd) {
		UssdResponse ret = new UssdResponse();
		String txt = "";
		txt = constructMenu(new String[] {"999909876543"},  Commands.END, bIncludeCmd);
		ret.setText(txt);
		ret.setCmd(Commands.END);
		return ret;
	}

}
