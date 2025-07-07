package org.mosip.ussd.sm.actions;

import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;
import org.mosip.ussd.util.Util;

public class RequestOTPHandler implements SMAction{

    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {

        System.out.println("Call OTP API for UIN cmdtext= "+ cmdText);
        String uin = context.getSessionManager().get("uin");
        if(uin == null || uin.equals("")){
            uin = cmdText;
            context.getSessionManager().put("uin",uin);
        }
        System.out.println("Call OTP API for UIN "+ uin);
        
        //generate TRID
		String trid = Util.genRandomNumbers(10);
        context.getSessionManager().put("TrId",trid);
        if(context.getConfig().getProps().get("useCredsAPI").equals("true"))
            context.getConfig().getIdCredsHelper().requestResidentOTP(uin, Util.ID_TYPE,trid, null);
        else
            context.getConfig().getResidentAPIHelper().requestResidentOTP(uin, Util.ID_TYPE,trid, null);
        // System.out.println("Call OTP API for UIN cmdtext= " + cmdText);
        // return "12345678";
            
        return null;
    }
    
}
