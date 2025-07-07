package org.mosip.ussd.sm.actions;

import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;

public class saveUinHandler implements SMAction{

    @Override
    public String execute(SMContext context,String cmdText, String sessionId) {
        
        context.getSessionManager().put("uin", cmdText);
        context.getConfig().getResidentService().updateResidentUin(context.getSessionManager().get("mobileNo"), cmdText);
        
                   
        return "";
    }
    
}
