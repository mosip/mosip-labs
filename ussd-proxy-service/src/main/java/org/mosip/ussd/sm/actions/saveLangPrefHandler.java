package org.mosip.ussd.sm.actions;

import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;

public class saveLangPrefHandler implements SMAction{

    @Override
    public String execute(SMContext context,String cmdText, String sessionId) {
        String lang = cmdText.equals( "2") ? "hi":"en";
        context.getSessionManager().put("lang", lang);
        context.getConfig().getResidentService().updateResidentLangCode(context.getSessionManager().get("mobileNo"), lang);
       
        return "";
    }
    
}
