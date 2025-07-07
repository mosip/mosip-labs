package org.mosip.ussd.sm.actions;

import java.util.List;

import org.mosip.ussd.entity.Credentials;
import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;

public class listCredsHandler implements SMAction {

    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {
        String phoneNo = context.getSessionManager().get("mobileNo");
        List<Credentials> creds = context.getConfig().getCredentialService().getAllCredentials(phoneNo);
        String [] strCreds  = new String[creds.size()];
        int i=0;
        for(Credentials c: creds){
            String s = c.getId() +" "+ c.getName();
            strCreds[i++] = s;
        }
        String ret = "";
        for(String s: strCreds){
            ret += s +"\n";
        }
       
        return ret;
    }
    
}
