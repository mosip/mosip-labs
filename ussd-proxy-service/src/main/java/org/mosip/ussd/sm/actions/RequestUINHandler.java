package org.mosip.ussd.sm.actions;

import org.mosip.ussd.sm.SMAction;
import org.mosip.ussd.sm.models.SMContext;

public class RequestUINHandler implements SMAction {

    @Override
    public String execute(SMContext context, String cmdText, String sessionId) {
        System.out.println("RequestUIN "+ cmdText);
        return null;
    }
    
}
