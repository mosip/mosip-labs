package org.mosip.ussd.sm;

import org.mosip.ussd.sm.models.SMContext;

public interface SMAction {
    public String execute(SMContext context,String cmdText, String sessionId);
}
