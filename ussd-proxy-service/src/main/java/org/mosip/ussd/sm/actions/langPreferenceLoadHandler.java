package org.mosip.ussd.sm.actions;

import org.mosip.ussd.entity.Resident;
import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;

public class langPreferenceLoadHandler implements SMAction{
    @Override
    public String execute(SMContext context,String cmdText, String sessionId) {
     //  return context.getSessionManager().get("lang");
   
       
       Resident res = context.getConfig().getResidentService().getResident(context.getSessionManager().get("mobileNo"));
       if(res != null){
           context.getSessionManager().put("lang",res.getPrefLang());
           return res.getPrefLang();
       }
       return "en";
    } 
}
