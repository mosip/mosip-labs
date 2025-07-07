package org.mosip.ussd.sm.actions;

import org.mosip.ussd.service.CredentialClaimsService;
import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;

public class ClaimsHandler implements SMAction{

    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {
        
        String txt = null;
		CredentialClaimsService credClaim = context.getConfig().getCredentialClaimsService();
        //new CredentialClaimsService(credentialService);
		int optionVal = Integer.parseInt(context.getSessionManager().get("claimsMenuId"));
		Boolean bRet  = false;
        Long credId = Long.parseLong(cmdText);
        //Long.parseLong(context.getSessionManager().get("credentialId"));

		switch(optionVal){
			case 1: //is above 18?
				bRet = credClaim.isAgeBetween(credId, 18, 120);
			    break;
			case 2:
			    bRet = credClaim.isAgeBetween(credId, 0, 5);
			    break;
			case 3:
			    bRet = credClaim.isAgeBetween(credId, 60, 120);
			    break;
		}
		txt = bRet ? "Yes": "No";	
        return txt;
    }
    
}
