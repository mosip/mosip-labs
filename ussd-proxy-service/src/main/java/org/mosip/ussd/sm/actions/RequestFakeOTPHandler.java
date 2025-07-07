package org.mosip.ussd.sm.actions;

import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;
// import org.mosip.ussd.util.Util;

public class RequestFakeOTPHandler implements SMAction{

    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {

       
        System.out.println("Call OTP API for UIN cmdtext= " + cmdText);
        return "12345678";
            
        // return null;
    }
    
}
