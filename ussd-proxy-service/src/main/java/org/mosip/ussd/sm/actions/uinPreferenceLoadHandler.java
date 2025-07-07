package org.mosip.ussd.sm.actions;

import org.mosip.ussd.entity.Resident;
import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;

public class uinPreferenceLoadHandler implements SMAction{
    @Override
    public String execute(SMContext context,String cmdText, String sessionId) {
    
        Resident res = context.getConfig().getResidentService().getResident(context.getSessionManager().get("mobileNo"));
        if(res != null){
            context.getSessionManager().put("uin",res.getVID());
            return res.getVID();
        }
        return "";
   //   (context.getSessionManager().get("mobileNo"), cmdText);
       
     // return context.getSessionManager().get("uin");
        //return "Enter UIN "+ sessionId;
    } 
}
